import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const models = JSON.parse(fs.readFileSync(path.join(root, 'src/data/modelDeployments.json'), 'utf8'));
const {runs} = JSON.parse(fs.readFileSync(path.join(root, 'src/data/modelValidationResults.json'), 'utf8'));
const latest = id => runs.map((run, index) => ({...run, index})).filter(run => run.modelId === id).sort((a,b) => b.date.localeCompare(a.date) || b.index-a.index)[0];
const sections = [
  ['detection','选择目标检测模型','目标检测输出目标类别、置信度和矩形框。通用场景可从 YOLO11 或 yolo26 开始；行业场景选择对应类别的专用模型。',['YOLO11','yolo26','YOLOv5','YOLOv8','RT-DETR','E_bike-axera','Helmet-axera','Person_car-axera','Fall-axera'],['行业权重只识别其训练类别，安全帽、车辆和跌倒模型不能互换。','静态图片中的 fall 标签不等于已经实现视频跌倒告警；视频业务还需要连续帧规则。'],'需要处理摄像头或文件视频时，先完成单张图片推理，再进入[视频处理](../usage/video.md)。'],
  ['segmentation','选择分割与去背景模型','实例分割为每个目标生成掩码；语义分割按像素分配类别；去背景则保留前景并输出透明通道。按需要的输出选择模型。',['YOLO11-Seg','yolo26-seg','YOLOv8-Seg','DeepLabv3Plus','RMBG-1.4','MobileSAM'],['检测框正确不能代替掩码检查，重点比较物体边缘、遮挡和细小结构。','RMBG 输出的透明 PNG 与彩色分割标签含义不同；集成时保留 Alpha 通道。'],'各模型的下载命令、程序入口和实际结果图均在对应部署页。'],
  ['pose','选择人体姿态模型','人体姿态模型输出关键点与骨架。先用固定图片确认坐标和连线，再替换成自己的单人或多人图片。',['YOLO11-Pose','yolo26-pose','YOLOv8-Pose','RTMPose'],['检查左右关节、低置信度点和被画面截断的人体，不把所有可见连线视为正确。','不同模型的检测、裁剪与关键点解码流程不同，不能只更换权重文件。'],'动作识别、跨帧跟踪和视频告警属于后续应用处理，另见[视频处理](../usage/video.md)。'],
  ['depth','选择深度估计模型','从单张图片生成深度层次图时，可选择 Depth-Anything-V2 或 Depth-Anything-3。各页提供对应程序与实测可视化。',['Depth-Anything-V2','Depth-Anything-3'],['当前展示的是相对深度，伪彩色和灰度值不能直接解释为米。','需要实际距离时，先确认模型的尺度定义，并使用已知距离或标定数据检查。'],'双目、多视图等方案可在[完整模型目录](catalog.mdx)检索；输入数量与相机参数需按其独立指南配置。'],
  ['open-vocabulary','选择开放词汇检测模型','需要通过文本词表指定检测对象时，先确认模型是否提供配套文本编码器或已计算的文本特征。词表是推理输入的一部分。',['YOLO-World-V2'],['文本特征、类别名称和输出索引必须一一对应；更换词表后重新生成配套特征。','先检查包含目标和不含目标的图片，再比较不同描述词带来的误检与漏检。'],'没有完整 AXCL 入口的模型按[自定义模型接入](custom-model.md)补齐前后处理。'],
  ['text-generation','选择文本对话模型','独立部署页提供准备环境、下载配套文件、启动服务和实际回复。短问答可从 Qwen3-0.6B 开始；需要翻译时可对照 HY-MT 页面的中英文样例。',['Qwen3-0.6B','Qwen3-0.6B-GPTQ-Int4','Qwen3-1.7B','Qwen3-1.7B-GPTQ-Int4','Qwen3-4B-GPTQ-Int4','Qwen3-4B','Qwen2.5-7B-Instruct-GPTQ-Int4','gemma-3-270m-it','Gemma-3-1B-it-AX650','MiniCPM5-1B','MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K','HY-MT1.5-1.8B_GPTQ_INT4'],['增加参数量、上下文或并发之前，用 axcl-smi 检查空闲 CMM；保留运行时的内存预检。','同一系列的量化、上下文规格和旧版脚本可能不同，配置、分词器与模型分片需要成套使用。','先检查实际回答再选型：算术错误、异常分词字符和 JSON 代码围栏均保留在各页，基本运行不表示内容或格式正确。'],'公共编译步骤见[AXCL 大模型运行时](llm-runtime.md)，应用调用见[服务接口](../usage/api-service.md)。'],
  ['vision-language','选择图像问答模型','图像问答需要视觉编码器与语言模型共同运行。进入具体部署页，可以下载同一张测试图片，发送问题并对照实际回复。',['FastVLM-1.5B-GPTQ-Int4','SmolVLM2-500M-Video-Instruct','Qwen3-VL-2B-Instruct-GPTQ-Int4','Qwen3.5-0.8B-AX650-GPTQ-Int4-C128-P1152-CTX2047','Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047','InternVL3_5-1B_GPTQ_INT4','InternVL3_5-2B_GPTQ_INT4','MiniCPM-V-4.6-GPTQ','qwenpaw-2b-flash-gptq-int4','Qwen3.5-0.8B-AX650-C128-P1152-CTX2047','Qwen3.5-2B-AX650-C128-P1152-CTX2047','Qwen3-VL-4B-Instruct-GPTQ-Int4','Qwen3.5-4B-AX650-GPTQ-Int4-C128-P1152-CTX2047','FastVLM-0.5B','FastVLM-1.5B'],['检查回答中的人数、对象和场景细节；流畅的句子也可能包含与画面不符的描述。','测试范围因模型而异，以各部署页的输入和结果为准。名称中含 Video 不代表该页面已验证视频。','达到 max_tokens 上限的回复会在效果区标注。要求简短回答或调整上限后重新运行，不把截断文本当作完整结果。'],'更多量化与上下文变体见[完整模型目录](catalog.mdx)，按具体版本进入部署页。'],
  ['speech-recognition','选择语音识别与声纹模型','语音转写输出文字，声纹比对输出说话人特征与相似度。先明确需要的结果，再选择相应模型。',['Whisper','SenseVoice','3D-Speaker','3D-Speaker-MT.Axera','3D-Speaker-Meeting-Summary'],['Whisper 页面使用当前模型包的 tiny 编码器、解码器与 Python 入口；旧 whisper.axcl 的三段权重不能混用。','3D-Speaker 的声纹分数不能代替语音转写或完整会议分段。','先处理短文件，再单独接入录音、静音检测、长音频分段和流式识别。'],'Whisper 与 SenseVoice 页可播放输入音频并查看实际转写；3D-Speaker 页展示两套声纹模型的录音与相似度。'],
  ['speech-synthesis','选择语音合成模型','语音合成把文本转换成音频。按需要的语言、音色和参考语音方式选择模型，并使用该页指定的字典、编码器与声码器。',['MeloTTS','CosyVoice2','CosyVoice3','ZipVoice.AXERA'],['不同包的 tokens、lexicon、说话人特征和声码器不能互换。','生成 WAV 后需要播放，检查发音、停顿、杂音和尾部截断；文件存在不等于语音质量通过。'],'MeloTTS 页提供三段中文实测音频，可直接播放并对照输入文本；其他模型按各页状态选择。'],
  ['extensions','选择 OCR、检索与图像增强模型','根据应用需要的最终输出选择模型：文字、向量、放大图像或局部特征。各页给出独立步骤与对应效果。',['PPOCR_v5','PPOCR_v6','PaddleOCR-VL-1.5','Plate-axera','Qwen3-Embedding-0.6B','clip','MobileCLIP','Real-ESRGAN','superpoint','Bird-Species-Classification'],['OCR 需要同时检查文字框和识别文本；向量检索需要比较匹配与不匹配输入的相似度。','图像增强应比较实际输出尺寸和细节；生成更大图片不等于新增了真实细节。','更换向量模型、归一化或预处理后，需要重新生成索引。'],'没有配套 AXCL 程序时，按[自定义模型接入](custom-model.md)完成前后处理。'],
];

for (const [slug,title,intro,ids,notes,next] of sections) {
  const rows = ids.map(id => {
    const model = models.find(item => item.id === id);
    if (!model) throw new Error(`Unknown task-guide model: ${id}`);
    const run = latest(id);
    const state = run?.status === 'passed' ? run.level === 'correctness' ? '固定样例已核对' : '已运行，效果仍需评估' : run?.status === 'blocked' ? '本次部署受阻' : run?.status === 'failed' ? '本次运行未通过' : '本机尚未实测';
    return `| [${id}](deploy/${model.slug}.md) | ${model.task} | [${state}](deploy/${model.slug}.md#查看部署效果) |`;
  }).join('\n');
  const text = `---\ntitle: ${JSON.stringify(title)}\n---\n\n# ${title}\n\n${intro}\n\n## 进入模型部署页\n\n| 模型 | 输出或用途 | 本机效果 |\n|---|---|---|\n${rows}\n\n点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。\n\n## 确认使用条件\n\n${notes.map(note => '- ' + note).join('\n')}\n\n${next}\n`;
  fs.writeFileSync(path.join(root, 'docs/models', slug + '.md'), text);
}
console.log(`Generated ${sections.length} task selection guides without duplicate deployment commands.`);
