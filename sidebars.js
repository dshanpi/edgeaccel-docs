// User-guide navigation. Source re-imports do not overwrite this file.
import modelSidebar from './src/data/modelSidebar.json';
export default {
  "docsSidebar": [
    "overview",
    "ax650n/roadmap",
    {
      "type": "category",
      "label": "接卡与安装",
      "collapsed": true,
      "items": [
        "getting-started/hardware",
        "ax650n/user-guide",
        "getting-started/prepare",
        "ax650n/quick-start/arm64",
        "ax650n/quick-start/linux-x86",
        "ax650n/quick-start/windows"
      ]
    },
    {
      "type": "category",
      "label": "完成首次推理",
      "collapsed": false,
      "items": [
        "usage/first-inference",
        "usage/device-check",
        "usage/download-models",
        "usage/build-samples"
      ]
    },
    {
      "type": "category",
      "label": "选择与部署模型",
      "collapsed": false,
      "items": [
        "models/selection",
        "models/catalog",
        {
          "type": "category",
          "label": "选择视觉模型",
          "collapsed": true,
          "items": [
            "models/detection",
            "models/segmentation",
            "models/pose",
            "models/depth",
            "models/open-vocabulary"
          ]
        },
        {
          "type": "category",
          "label": "选择文本与多模态模型",
          "collapsed": true,
          "items": [
            "models/llm-runtime",
            "models/text-generation",
            "models/vision-language"
          ]
        },
        {
          "type": "category",
          "label": "选择语音与扩展模型",
          "collapsed": true,
          "items": [
            "models/speech-recognition",
            "models/speech-synthesis",
            "models/extensions",
            "models/custom-model"
          ]
        },
        {
          "type": "category",
          "label": "模型部署与效果",
          "collapsed": true,
          "items": modelSidebar
        }
      ]
    },
    {
      "type": "category",
      "label": "接入应用与维护",
      "collapsed": true,
      "link": {"type": "doc", "id": "usage/application-guide"},
      "items": [
        {
          "type": "category",
          "label": "接入应用",
          "collapsed": false,
          "items": ["usage/python", "usage/api-service", "usage/video"]
        },
        {
          "type": "category",
          "label": "运行与维护",
          "collapsed": false,
          "items": [
            "usage/performance", "usage/maintenance", "usage/troubleshooting",
            {
              "type": "category",
              "label": "RK3576 指定版本内核头",
              "collapsed": true,
              "items": [
                "ax650n/reference/kernel-headers/install",
                "ax650n/reference/kernel-headers/fixes"
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "category",
      "label": "项目实战",
      "collapsed": false,
      "items": [
        {
          "type": "category",
          "label": "AX8850 六路 AI 视频推流",
          "collapsed": true,
          "link": {"type": "doc", "id": "projects/six-streams"},
          "items": [
            "ax650n/applications/six-streams/prepare",
            "ax650n/applications/six-streams/implementation",
            "ax650n/applications/six-streams/usage",
            "ax650n/applications/six-streams/local-preview",
            "ax650n/applications/six-streams/validation",
            "usage/services",
            "ax650n/applications/six-streams/frame-rate",
            "ax650n/applications/six-streams/inference",
            "ax650n/applications/six-streams/vlc-troubleshooting"
          ]
        },
        "projects/laya-games"
      ]
    },
    {
      "type": "category",
      "label": "检查方法与参考",
      "collapsed": true,
      "items": [
        "reference/validation",
        "reference/glossary",
        "reference/sources",
        "downloads"
      ]
    }
  ]
};
