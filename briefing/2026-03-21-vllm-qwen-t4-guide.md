---
title: "Running vLLM with 4 Nvidia T4 GPUs for Qwen3.5-35B GPTQ Int4"
date: 2026-03-21T20:00:00+08:00
draft: false
tags: ["vLLM", "GPU", "LLM", "Qwen", "GPTQ", "Distributed Inference", "T4", "Multi-GPU"]
categories: ["AI", "Infrastructure", "Technical Guide"]
description: "Comprehensive guide to running Qwen3.5-35B GPTQ Int4 on 4× Nvidia T4 16GB GPUs using vLLM with tensor parallelism. Includes architecture, configuration, performance analysis, and troubleshooting."
---

## Executive Summary

Running Qwen3.5-35B GPTQ Int4 on 4× Nvidia T4 16GB GPUs is **feasible with vLLM** through tensor parallelism, distributing model computation across all GPUs. The Qwen3.5-35B model (35B total parameters with 3B activated via MoE) has an estimated GPTQ Int4 footprint of approximately 8-10 GB, which requires tensor parallelism across all 4 GPUs (totaling 64GB) to achieve optimal performance.

vLLM's architecture, built on PagedAttention for efficient memory management and GPTQ quantization support, enables this configuration to deliver reasonable throughput for inference workloads while staying within T4 GPU memory constraints. However, performance will be substantially lower than on higher-end GPUs due to T4's limited PCIe bandwidth (16× Gen3) and lower FP32 compute capability.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    vLLM Inference Engine                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LLM Instance (Qwen3.5-35B-GPTQ-Int4)                       │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  Tensor Parallel Coordinator (TP=4)                   │  │   │
│  │  │  - Distributes model layers across 4 GPUs             │  │   │
│  │  │  - Coordinates all-gather/reduce-scatter operations   │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │              │              │              │           │
│      GPU0 │         GPU1 │         GPU2 │         GPU3 │           │
│ (16GB)    │ (16GB)       │ (16GB)       │ (16GB)       │           │
│      T4   │         T4   │         T4   │         T4   │           │
│           │              │              │              │           │
└───────────┼──────────────┼──────────────┼──────────────┘           │
            │              │              │              │            │
           PCIe Gen3 x16 interconnect (8GB/s per link)              │
            │              │              │              │            │
            └──────────────────────────────────────────┘             │
                                                                      │
              OpenAI-compatible Server Interface                      │
                      (Port 8000)                                     │
```

## Qwen3.5-35B Model Specifications

Qwen3.5-35B-A3B is an efficient hybrid-architecture model with sparse mixture-of-experts (MoE):

- **Total Parameters**: 35B
- **Activated Parameters**: 3B (via sparse MoE routing)
- **Hidden Dimension**: 2048
- **Context Length**: 262,144 tokens (natively), extensible to 1,010,000
- **Quantization**: GPTQ 4-bit (Int4)
- **Architecture**: Gated Delta Networks + Sparse MoE (256 experts, 8 routed + 1 shared)

### Sparse Architecture Design

The model uses an innovative hybrid layout with 10 layers featuring:
- 3 layers with: Gated DeltaNet → MoE → Gated Attention → MoE
- 1 layer with: Gated Attention → MoE
- Linear Attention: 32 heads (V) / 16 heads (QK) with 128D head dimension
- Standard Attention: 16 heads (Q) / 2 heads (KV) with 256D head dimension

### GPTQ Int4 Quantization Benefits

GPTQ quantization reduces the model to 4-bit precision using post-training quantization:

- **Memory Reduction**: ~4× compression compared to FP16 (35B parameters)
- **Unquantized Equivalent VRAM**: ~70GB (FP16)
- **GPTQ Int4 VRAM**: ~17.5GB (base model weights)
- **Inference Speedup**: 3.25× on A100; lower on T4 due to architecture differences
- **Dequantization**: Done on-the-fly in fused kernels rather than global memory

This makes the Qwen3.5-35B GPTQ model viable for multi-GPU T4 deployments.

## vLLM Framework

vLLM is an open-source framework for fast LLM serving, originally developed at UC Berkeley's Sky Computing Lab.

### Key Innovations

- **PagedAttention**: Virtual memory-inspired algorithm that manages KV cache efficiently with near-zero memory fragmentation
- **Continuous Batching**: Incoming requests batched dynamically without waiting for sequences to complete
- **CUDA Graph Execution**: Optimized execution with minimal CPU-GPU synchronization overhead
- **Quantization Support**: Native support for GPTQ, AWQ, AutoRound, INT4, INT8, and FP8 quantization

### Parallelism Strategies

vLLM supports multiple distributed inference patterns:
- **Tensor Parallelism (TP)**: Splits model layers across GPUs; requires all-gather/reduce-scatter communication
- **Pipeline Parallelism (PP)**: Splits model pipeline stages across GPUs
- **Expert Parallelism**: For MoE models; distributes experts across GPUs
- **Data Parallelism**: Processes multiple independent requests in parallel

## Multi-GPU Configuration Strategy

### Recommended Setup

```python
from vllm import LLM, SamplingParams

# Initialize with tensor parallelism across 4 T4 GPUs
llm = LLM(
    model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
    tensor_parallel_size=4,
    dtype="auto",  # Respects quantization format
    gpu_memory_utilization=0.85,  # Conservative for T4
    max_model_len=16384,  # Context length; adjust based on memory
    trust_remote_code=True,
)
```

### Rationale for TP=4

1. **Model Fit**: With GPTQ Int4 compression (~17.5GB) + KV cache + activations, requires distribution across 4 GPUs
2. **Activation Distribution**: Each GPU holds ~1/4 of model parameters + ~1/4 of activations during inference
3. **Communication Overhead**: Tensor parallelism feasible over PCIe Gen3 x16
4. **MoE Routing**: Qwen3.5-35B's sparse experts benefit from expert parallelism

### Memory Budget Breakdown (Per GPU)

| Component | Size | Notes |
|-----------|------|-------|
| Model Weights (GPTQ Int4) | ~4.4 GB | 35B params × 4-bit / 4 GPUs |
| Embedding Layers | ~0.5 GB | Shared or replicated |
| KV Cache (seq_len=2048) | ~2-3 GB | Per sequence; scales with batch size |
| Activations | ~1-2 GB | Forward pass intermediate tensors |
| Overhead | ~1 GB | vLLM's PagedAttention mitigates fragmentation |
| **Total (target)** | **~10-11 GB** | Within 16GB T4 VRAM with safety margin |

## Installation & Setup

### Environment Setup

```bash
# 1. Install CUDA Toolkit 12.1 or higher
sudo apt update
sudo apt install -y nvidia-cuda-toolkit nvidia-cudnn

# 2. Install vLLM with CUDA support
pip install vllm

# 3. Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers>=4.40 peft accelerate

# 4. Download model (optional; vLLM downloads on first run)
huggingface-cli download Qwen/Qwen3.5-35B-A3B-GPTQ-Int4 \
    --cache-dir /path/to/cache
```

### Docker Configuration

For reproducible multi-GPU environments:

```dockerfile
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip git

WORKDIR /app

# Install vLLM
RUN pip install vllm torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

EXPOSE 8000

CMD ["python", "-m", "vllm.entrypoints.openai.api_server", \
     "--model", "Qwen/Qwen3.5-35B-A3B-GPTQ-Int4", \
     "--tensor-parallel-size", "4", \
     "--gpu-memory-utilization", "0.85"]
```

**Docker Run Command**:
```bash
docker run --gpus all \
    -p 8000:8000 \
    -v /path/to/models:/models \
    vllm-qwen35b:latest
```

## Inference Configuration

### OpenAI-Compatible API Server

```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3.5-35B-A3B-GPTQ-Int4 \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 16384 \
    --quantization gptq \
    --port 8000
```

### Offline Inference (Python)

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
    tensor_parallel_size=4,
    gpu_memory_utilization=0.85,
    quantization="gptq",
    max_model_len=16384,
)

sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.95,
    max_tokens=512,
)

prompts = [
    "Translate 'hello' to French",
    "What is machine learning?"
]

outputs = llm.generate(prompts, sampling_params)
for output in outputs:
    print(f"Prompt: {output.prompt}")
    print(f"Generated: {output.outputs[0].text}\n")
```

## Performance Characteristics

### Throughput Estimates

**T4 Tensor Parallelism Bottlenecks**:

| Metric | Value | Impact |
|--------|-------|--------|
| Memory Bandwidth (per GPU) | 320 GB/s | Sufficient for inference |
| PCIe Gen3 x16 Bandwidth | ~16 GB/s per GPU | Bottleneck for model loading |
| Cross-GPU Communication | 8 GB/s effective per link | Limits tensor parallelism efficiency |
| FP32 Compute (per T4) | 8.1 TFLOPS | Limited; GPTQ dequant helps |
| INT4 Compute (per T4) | 260 INT4 TOPS | GPTQ dequantization leverages this |

**Projected Throughput**:
- **Batch Size 1, Seq Len 512**: ~10-20 tokens/second
- **Batch Size 4, Seq Len 2048**: ~40-60 tokens/second (distributed across 4 GPUs)
- **Maximum Batch**: Limited by KV cache; ~8-16 sequences with 16384 ctx length

### Communication Overhead

Tensor parallelism on T4 incurs all-gather/reduce-scatter communication during attention computation. With `tensor_parallel_size=4` on T4s, communication overhead is **~15-25%** of total latency due to limited PCIe bandwidth.

## Optimization Techniques

### 1. Context Length Optimization

```python
llm = LLM(
    model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
    tensor_parallel_size=4,
    max_model_len=8192,  # Reduce from native 262K
    gpu_memory_utilization=0.85,
)
```

Benefit: Smaller KV cache → larger batch sizes or reduced latency.

### 2. Speculative Decoding

Use a smaller draft model to predict future tokens, verified by the large model:

```python
llm = LLM(
    model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
    tensor_parallel_size=4,
    speculative_model="Qwen/Qwen2-7B-Instruct-GPTQ-Int4",
    num_speculative_tokens=5,
)
```

### 3. Prefix Caching

Cache and reuse KV caches for repeated prefixes:

```python
llm = LLM(
    model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
    tensor_parallel_size=4,
    enable_prefix_caching=True,
)
```

### 4. Chunked Prefill

Process input prefixes in chunks to reduce peak memory:

```python
llm = LLM(
    model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
    tensor_parallel_size=4,
    enable_chunked_prefill=True,
    max_seq_len_to_capture=2048,
)
```

## Troubleshooting

### Out-of-Memory (OOM) Errors

**Solutions**:
1. Reduce `gpu_memory_utilization`: `gpu_memory_utilization=0.75`
2. Reduce `max_model_len`: `--max-model-len 4096`
3. Batch size reduction (automatic in vLLM's continuous batching)

### Slow Inference Speed

**Causes & Solutions**:
- PCIe Saturation: Increase batch size to amortize communication cost
- CPU-GPU Sync: Enable CUDA graph mode (default in vLLM)
- Memory Fragmentation: Already mitigated by PagedAttention
- Suboptimal Hardware: T4 is older architecture; use speculative decoding

### Model Loading Timeout

**Solution**:
```bash
huggingface-cli download Qwen/Qwen3.5-35B-A3B-GPTQ-Int4 \
    --cache-dir /data/models

export HF_HOME=/data/models
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3.5-35B-A3B-GPTQ-Int4 \
    --tensor-parallel-size 4
```

## Deployment Considerations

### Production Monitoring

Track key metrics:
```bash
# Monitor GPU utilization during inference
watch nvidia-smi

# Monitor vLLM metrics (if enabled)
curl http://localhost:8000/metrics
```

**Key Metrics**:
- GPU Memory Usage (should stabilize after warmup)
- GPU Utilization (target: 70-90%)
- Request Latency (p50, p99)
- Tokens/second throughput
- Queue depth (pending requests)

### Cost Analysis

**T4 Instance Costs**:
- Google Cloud: ~$0.15-0.25 per T4-GPU per hour
- AWS: ~$0.35 per T4-GPU per hour
- 4× T4 Deployment: ~$0.60-1.00/hour

vs. Single A100 (~$3-5/hour): T4 cluster is more cost-effective for lower throughput or batch workloads.

## Best Use Cases

✅ **Good Fits for T4 Deployment**:
- Batch inference (off-line processing)
- Non-real-time chatbot systems
- Content generation with moderate latency
- API serving with moderate QPS (queries per second)
- Cost-sensitive production deployments
- Development/testing before A100 production

❌ **Poor Fits**:
- Real-time low-latency inference (<100ms)
- Extremely long-context reasoning (>32K tokens)
- High-QPS production systems (>100 QPS)
- Time-sensitive interactive applications
- Multi-turn conversation with long memory

## Conclusion

Running Qwen3.5-35B GPTQ Int4 on 4× Nvidia T4 16GB GPUs is a practical and cost-effective solution for many inference workloads. While performance is limited compared to newer GPU architectures, the combination of GPTQ quantization, tensor parallelism, and vLLM's optimizations makes this configuration viable for batch processing, development, and moderate-throughput production systems.

The key to success is understanding the hardware constraints (PCIe bandwidth, memory per GPU) and tuning vLLM's configuration parameters appropriately. For throughput-oriented applications where sub-100ms latency isn't required, this setup delivers excellent value.

---

**References**:
- vLLM Project: https://github.com/vllm-project/vllm
- Qwen3.5-35B Model: https://huggingface.co/Qwen/Qwen3.5-35B-A3B-GPTQ-Int4
- GPTQ Paper: https://arxiv.org/abs/2210.17323
- vLLM Paper (PagedAttention): https://arxiv.org/abs/2309.06180
- NVIDIA T4 Specifications: https://nvidia.com/en-us/data-center/tesla-t4/
