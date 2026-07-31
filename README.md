# BNCT Dose Engine (MYP)

硼中子俘获治疗 (BNCT) 多线程粒子输运剂量模拟引擎，使用 **MYP 语言** 编写。

## 特性

- 多线程粒子输运（`@parallel for`，16 线程）
- H-1 弹性散射 / 俘获
- O-16 弹性散射
- B-10 俘获
- 事件驱动 + 映射 (Mapping) 架构
- 原子计数 (Atomic) 线程安全累加
- 支持 1e9 粒子规模模拟

## 依赖

- [MYP 语言编译器](https://github.com/laomen/MypLanguage) (`mypc`)
- HDF5 (`libhdf5-dev`)

## 构建

```bash
# 1. 先构建 MYP 编译器 (见 MypLanguage 仓库)
cd MYPLanguage
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=/usr/lib/llvm-21/lib/cmake/llvm
make -j$(nproc)

# 2. 构建 DoseEngine
cd BNCTDoseEngine
mkdir build && cd build
cmake .. -DMYPLANG_ROOT=/path/to/MYPLanguage
make -j$(nproc)
```

> 也可以通过环境变量 `MYPLANG_ROOT` 指定 MYP 工具链路径，无需 `-DMYPLANG_ROOT`。

## 运行

```bash
./build/sim
```

程序输出剂量分布结果到 `results/` 目录。

## 模块

| 模块 | 职责 |
|------|------|
| `mapping_demo.myp` | 主入口，事件链编排 |
| `source.myp` | 粒子源 |
| `transport.myp` | 粒子输运引擎（并行） |
| `physics.myp` | 物理过程 |
| `xs_data.myp` / `xs_loader.myp` | 截面数据加载 |
| `cross_section_db.myp` | 截面数据库 |
| `tally.myp` | 剂量统计 |
| `material.myp` / `nuclide.myp` | 材料与核素 |
| `mesh.myp` | 空间网格 |
| `data_manager.myp` | 数据管理 |
| `hdf5.myp` / `hdf5_bridge.c` | HDF5 数据桥接 |
| `logger.myp` | 日志 |

详见 [ARCHITECTURE.md](ARCHITECTURE.md)。
