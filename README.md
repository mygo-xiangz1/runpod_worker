# runpod_worker — 脱衣 Agent 的 RunPod Serverless ComfyUI 镜像

这个仓库喂给 **RunPod GitHub 集成** 自动构建（不需要本机 Docker）。

## 文件

```
Dockerfile                              # RunPod 构建入口（30 分钟限制内轻松完成：只装代码，不下载模型）
custom_nodes/ComfyUI-PhotoTexture/      # 闭源质感节点（纯 torch，零依赖），vendor 自本机 F 盘
```

## 镜像内容（对照生产 run_one.py 的 12 个 class_type）

| 节点类 | 来源 |
|---|---|
| UnetLoaderGGUF | registry `comfyui-gguf` |
| QwenImage21Cache / TextEncodeQwenImage21 | ComfyUI **v0.39.1**（基础镜像自带 0.34.0 没有 → Dockerfile 里 checkout 升级） |
| RTXVideoSuperResolution | registry `comfyui_nvidia_rtx_nodes` + pip `nvidia-vfx`（双 venv 都装） |
| LocalPhotoTextureAdjust | 本仓库 vendored |
| CLIPLoader / VAELoader / KSampler / SaveImage / LoadImage / SplitImageWithAlpha / VAEDecode / LoraLoaderModelOnly | ComfyUI 核心自带 |

模型 **不进镜像**：挂在网络卷 `w22g0ppd6q` 顶层 `models/`（worker 自动映射 `/runpod-volume/models/*`）。

## 部署（RunPod Console，5 步）

1. GitHub 建 **public** 仓库（如 `runpod_worker`），把本目录整体推上去。
2. RunPod Console → **Settings → Connections → GitHub → Connect** 授权该仓库。
3. **Serverless → New Endpoint → Import Git Repository** 选它，Branch `main`，Dockerfile Path `Dockerfile`。
4. GPU 类型选 **RTX 5090**（至少 24GB；先别选多区域）；Volume 挂 `w22g0ppd6q`（**必须同区域 eu-ro-1**）；Active Workers=1，其余默认。
5. Deploy → **Builds** 页等到 `Completed`（预计 5–15 分钟）→ Workers 到 `Idle` 后即可收请求。

## 更新

改完代码 push 后，给仓库打个 **git tag（release）** 才会触发重建，普通 push 不触发。
