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
const latestRuns = new Map();
for (const run of validation.runs.filter(run => modelIds.has(run.modelId))) {
  const previous = latestRuns.get(run.modelId);
  if (!previous || run.date >= previous.date) latestRuns.set(run.modelId, run);
}
const runs = [...latestRuns.values()];
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
import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 查找模型的部署文档

<GuideHero label="模型索引 · 部署与效果" title="从任务找到模型，从结果确认配置" description="按名称、任务、资料状态与实测记录缩小范围，在独立部署页完成准备、下载、运行和效果检查。" facts={${JSON.stringify([['模型与应用', `${models.length-resources} 个条目`], ['工具与资源', `${resources} 个条目`], ['使用顺序', '选模型 → 看效果 → 部署']])}} />

还未确定具体型号，先看[按任务和容量选择模型](selection.mdx)。已选定型号，可直接搜索名称；首次运行前完成[环境与设备检查](../usage/device-check.md)。

${runs.length ? `按每个模型的最近一条记录统计：**${passedCount} 个已运行**，其中 ${passedCorrectness} 个完成固定样例核对、${passedBasic} 个仍需评估效果。历史记录与其他权重的结果在独立页面查看。` : '**当前尚无本机实测记录。** 各页说明接入条件及待检查的输出。'}

效果展示仅覆盖页面列明的模型文件、环境和输入。同仓库的其他权重、芯片目标或上下文规格需分别验证，不能从一个样例推断全部变体通过。

## 查找独立文档

1. **先选任务类别**，或输入型号关键词，例如 Qwen3、YOLO、语音。
2. **再看资料与实测状态**：前者说明入口是否齐备，后者说明具体配置运行到了哪一步。
3. **进入部署页核对容量和版本**，下载同一组配套文件，先复现页面样例。

<ModelCatalog />

## 判断能否开始部署

<details>
<summary>查看各类资料状态的数量</summary>

| 资料状态 | 条目数 |
|---|---:|
${counts}

</details>

| 资料状态 | 进入页面后要做什么 |
| --- | --- |
| 有 AXCL 部署步骤 / Python 步骤 | 核对该页硬件环境与实测状态，再按已整理的命令运行。 |
| 有 AXCL 专用脚本 | 匹配主机架构、专用程序、分词器及设备配置，使用该页入口。 |
| 需匹配运行时与配置 / 需确认 AXCL 适配 / 有 AXCL Python 线索 | 先补齐页面列明的条件，再进行加载和输出检查。 |
| 非本卡编译目标 / 需多卡配置 / 已知 AXCL 限制 | 按要求另选目标权重、准备对应硬件或确认问题修复。 |
| 工具与配套资源 | 按资源用途使用，不作为神经网络模型加载。 |

资料状态与实测状态分别判断。有操作步骤不等于当前容量已通过；某条记录受阻也不抹去其他版本的历史结果。

## 查看运行后的效果

点击表格中的“查看部署效果”，直接进入对应模型页面的结果区。视觉模型展示原图与结果图，问答模型展示实际输入和回复，语音模型展示音频或转写，向量模型展示对比结果。样例环境、耗时和文件版本可在同页展开查看。

本机尚未实测的模型只列出预期输出和当前接入条件，不将上游演示或性能当成本卡结果。

## 保存最终选择

确定模型后，保存仓库 revision、权重路径、运行程序与配置、卡容量、输入样例和结果。换量化版本、上下文或芯片目标时，作为新的部署组合重新检查。

<GuideNext items={[{to: '/docs/models/selection', title: '返回任务与容量选型', text: '先明确业务输出，再确定资源预算。'}, {to: '/docs/models/custom-model', title: '接入目录外的模型', text: '准备源模型、转换配置与参考结果。'}]} />

来源：[AXERA-TECH 模型组织页](https://huggingface.co/AXERA-TECH)。后续新增仓库在下次核对时纳入，本清单不自动代表实时组织内容。
`;
const output = path.join(root, 'docs/models/catalog.mdx');
if (!fs.existsSync(output) || fs.readFileSync(output, 'utf8') !== body) {
  fs.writeFileSync(output, body);
}
console.log(`Generated catalog: ${models.length} repositories, ${resources} resources.`);
