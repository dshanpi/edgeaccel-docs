export const learningRoadmaps = {
  "ax650n": {
    "id": "edgeaccel-card-guide-v2",
    "part": "M.2 算力卡",
    "title": "算力卡使用路线",
    "subtitle": "完成安装和首次推理，再按任务部署模型",
    "sourceTitle": "EdgeAccel 使用指南",
    "version": "资料整理版 · 2026 年 9 月",
    "platform": "ARM64 · Linux x86_64 · Windows 安装入口",
    "outcome": "完成所选模型的实际输入验证并保存结果。",
    "goals": [
      "确认硬件与配套软件",
      "使用 AXCL 后端运行模型",
      "按任务选择兼容模型包",
      "记录真实结果与资源占用"
    ],
    "chapters": [
      {
        "id": "prepare",
        "number": "01",
        "title": "确认配套文件",
        "shortTitle": "确认配套文件",
        "href": "/docs/getting-started/prepare",
        "description": "确认卡容量、主机架构与 PAC。",
        "outcome": "确认卡容量、主机架构与 PAC。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": false,
        "prerequisites": []
      },
      {
        "id": "install",
        "number": "02",
        "title": "完成主机安装",
        "shortTitle": "完成主机安装",
        "href": "/docs/ax650n/user-guide",
        "description": "选择一种主机平台，安装 AXCL 并检查设备。",
        "outcome": "选择一种主机平台，安装 AXCL 并检查设备。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": false,
        "prerequisites": [
          "prepare"
        ]
      },
      {
        "id": "first",
        "number": "03",
        "title": "运行真实图片",
        "shortTitle": "运行真实图片",
        "href": "/docs/usage/first-inference",
        "description": "Linux 主机选择脚本运行或手动操作；Windows 按平台指南操作。",
        "outcome": "完成所选操作方式，打开结果图片并核对检测框与类别。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": false,
        "prerequisites": [
          "install"
        ]
      },
      {
        "id": "choose",
        "number": "04",
        "title": "选择模型",
        "shortTitle": "选择模型",
        "href": "/docs/models/catalog",
        "description": "按任务、容量及 AXCL 状态选择模型包。",
        "outcome": "按任务、容量及 AXCL 状态选择模型包。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": false,
        "prerequisites": [
          "first"
        ]
      },
      {
        "id": "llm",
        "number": "05",
        "title": "文本与多模态",
        "shortTitle": "文本与多模态",
        "href": "/docs/models/llm-runtime",
        "description": "先完成文本对话，再增加视觉输入。",
        "outcome": "先完成文本对话，再增加视觉输入。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": true,
        "prerequisites": [
          "choose"
        ]
      },
      {
        "id": "speech",
        "number": "06",
        "title": "语音应用",
        "shortTitle": "语音应用",
        "href": "/docs/models/speech-recognition",
        "description": "使用配套程序验证语音输入与输出。",
        "outcome": "使用配套程序验证语音输入与输出。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": true,
        "prerequisites": [
          "choose"
        ]
      },
      {
        "id": "video",
        "number": "07",
        "title": "视频与应用接入",
        "shortTitle": "视频与应用接入",
        "href": "/docs/usage/video",
        "description": "从单路视频逐步增加负载。",
        "outcome": "从单路视频逐步增加负载。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": true,
        "prerequisites": [
          "choose"
        ]
      },
      {
        "id": "validate",
        "number": "08",
        "title": "检查与保存自己的结果",
        "shortTitle": "检查与保存自己的结果",
        "href": "/docs/reference/validation",
        "description": "先在模型页对照部署效果，再保存自己的输入与输出。",
        "outcome": "先在模型页对照部署效果，再保存自己的输入与输出。",
        "evidence": [
          "操作记录",
          "实际输出与日志"
        ],
        "optional": false,
        "prerequisites": [
          "first"
        ]
      }
    ],
    "context": {
      "title": "从接卡到应用",
      "principle": "安装平台三选一；后续部署章节以 Linux 为主。进度只保存在当前浏览器，不代表设备验证状态。",
      "rows": [
        {
          "label": "准备环境",
          "detail": "安装与设备检查",
          "tone": "workspace",
          "items": [
            {
              "label": "确认配套文件",
              "chapterId": "prepare"
            },
            {
              "label": "完成主机安装",
              "chapterId": "install"
            }
          ]
        },
        {
          "label": "运行模型",
          "detail": "真实输入与模型选型",
          "tone": "workspace",
          "items": [
            {
              "label": "运行真实图片",
              "chapterId": "first"
            },
            {
              "label": "选择模型",
              "chapterId": "choose"
            }
          ]
        },
        {
          "label": "扩展任务",
          "detail": "按业务需要选择",
          "tone": "workspace",
          "items": [
            {
              "label": "文本与多模态",
              "chapterId": "llm"
            },
            {
              "label": "语音应用",
              "chapterId": "speech"
            },
            {
              "label": "视频与应用接入",
              "chapterId": "video"
            }
          ]
        },
        {
          "label": "保存证据",
          "detail": "正确性与稳定性",
          "tone": "workspace",
          "items": [
            {
              "label": "检查与保存自己的结果",
              "chapterId": "validate"
            }
          ]
        }
      ]
    }
  }
};
export function getLearningRoadmap(courseId) { return learningRoadmaps[courseId]; }
