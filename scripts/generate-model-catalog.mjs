import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const models = JSON.parse(fs.readFileSync(path.join(root, 'src/data/models.json'), 'utf8'));
const source = JSON.parse(fs.readFileSync(path.join(root, 'src/data/modelSourceSnapshot.json'), 'utf8'));
const validationPath = path.join(root, 'src/data/modelValidationResults.json');
const validation = fs.existsSync(validationPath)
  ? JSON.parse(fs.readFileSync(validationPath, 'utf8'))
  : {schemaVersion: 1, environments: [], runs: []};
const modelIds = new Set(models.filter(model => model.kind !== 'resource').map(model => model.id));
const runs = validation.runs.filter(run => modelIds.has(run.modelId));
const passed = runs.filter(run => run.status === 'passed');
const passedCount = new Set(passed.map(run => run.modelId)).size;
const passedBasic = new Set(passed.filter(run => run.level === 'basic').map(run => run.modelId)).size;
const passedCorrectness = new Set(passed.filter(run => run.level === 'correctness').map(run => run.modelId)).size;
const measuredCount = new Set(runs.map(run => run.modelId)).size;
const resources = models.filter(m=>m.kind==='resource').length;
const counts = [...new Set(models.map(m=>m.status))].map(status=>`| ${status} | ${models.filter(m=>m.status===status).length} |`).join('\n');
for(const model of models){
  if(!fs.existsSync(path.join(root,'docs',model.guide+'.md')))throw new Error(`Missing individual guide: ${model.id}`);
}
const body=`---
title: 模型目录与独立部署文档
description: 按型号、任务与 AXCL 适配状态查找 AXERA-TECH 模型的独立部署文档。
---

import ModelCatalog from '@site/src/components/ModelCatalog';

# 查找模型的部署文档

**${models.length-resources} 个模型与应用 · ${resources} 个工具资源**。按名称、任务或实测状态筛选，进入独立部署页查看步骤与结果。资料清单核对日期：${source.checkedAt}。

首次部署先完成[环境与设备检查](../usage/device-check.md)，再按型号进入对应页面。

${runs.length ? `**已有 ${passedCount} 个模型提供本机效果展示。** ${passedCorrectness} 个完成固定样例核对，${passedBasic} 个已运行但效果仍需评估。进入具体模型页，按下载、运行、查看效果的顺序操作。` : '**当前尚无本机效果展示。** 各页明确说明接入条件及待检查的输出。'}

效果展示仅覆盖页面列明的模型文件、环境和输入。同仓库的其他权重、芯片目标或上下文规格需分别验证，不能从一个样例推断全部变体通过。

## 查找独立文档

<ModelCatalog />

## 判断能否开始部署

<details>
<summary>查看各类资料状态的数量</summary>

| 资料状态 | 条目数 |
|---|---:|
${counts}

</details>

- **有 AXCL 部署步骤 / Python 步骤**：已核对程序接口和对应文件，提供该模型的命令；仍需硬件验证兼容性、容量和输出效果。
- **有 AXCL 专用脚本**：包内存在 AXCL 入口；按独立页面匹配主机架构、旧版程序、tokenizer 服务和设备配置。
- **需匹配运行时与配置 / 需确认 AXCL 适配 / 有 AXCL Python 线索**：提供已确认的文件、入口和接入条件，尚未形成可直接运行的完整组合。
- **非本卡编译目标 / 需多卡配置 / 已知 AXCL 限制**：按页面说明另选权重、配置多卡或等待问题修复，不按单卡通用流程启动。
- **工具与配套资源**：提供资源用途和安装入口，不作为神经网络模型加载。

## 查看运行后的效果

点击表格中的“查看部署效果”，直接进入对应模型页面的结果区。视觉模型展示原图与结果图，问答模型展示实际输入和回复，语音模型展示音频或转写，向量模型展示对比结果。样例环境、耗时和文件版本可在同页展开查看。

本机尚未实测的模型只列出预期输出和当前接入条件，不将上游演示或性能当成本卡结果。

来源：[AXERA-TECH 模型组织页](https://huggingface.co/AXERA-TECH)。后续新增仓库在下次核对时纳入，本清单不自动代表实时组织内容。
`;
fs.writeFileSync(path.join(root,'docs/models/catalog.mdx'),body);
console.log(`Generated catalog: ${models.length} repositories, ${resources} resources.`);
