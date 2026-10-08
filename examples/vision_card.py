"""Run fixed upstream vision examples on an AXCL card and save fresh outputs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import string
import sys
import time

import axengine
import cv2
import numpy as np


def module(path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("upstream_example", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--task", choices=["realesrgan", "rf-detr", "rf-detr-b2", "deimv2", "visdrone", "yolov5-seg", "dinov3", "mobileclip", "mixformer", "super-resolution", "satrn", "silero-vad", "siglip2", "yolov7-face"], required=True)
    parser.add_argument("--binary", type=Path, help="Locally built AXCL face detector")
    parser.add_argument("--variant", default="x2")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.model_dir.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    os.chdir(root)
    report = {"task": args.task, "variant": args.variant,
              "provider": "AXCLRTExecutionProvider", "sessions": [], "results": []}
    original_session = axengine.InferenceSession

    def save():
        (out / "deployment-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    class MeasuredSession:
        def __init__(self, model, **kwargs):
            if "AXCLRTExecutionProvider" not in axengine.get_available_providers():
                raise RuntimeError("AXCLRTExecutionProvider is unavailable; check the host AXCL installation")
            kwargs["providers"] = ["AXCLRTExecutionProvider"]
            self.session = original_session(model, **kwargs)
            self.record = {"model": str(Path(model).relative_to(root) if Path(model).is_absolute() else model),
                           "inputs": [{"name": v.name, "shape": list(v.shape), "dtype": str(v.dtype)} for v in self.session.get_inputs()],
                           "outputs": [{"name": v.name, "shape": list(v.shape)} for v in self.session.get_outputs()],
                           "runMilliseconds": [], "allFinite": True}
            report["sessions"].append(self.record)
            save()

        def __getattr__(self, key):
            return getattr(self.session, key)

        def run(self, names, feeds=None, **kwargs):
            if feeds is None:
                feeds = kwargs.pop("input_feed")
            start = time.perf_counter()
            values = self.session.run(names, feeds, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            self.record["runMilliseconds"].append(elapsed)
            if not all(np.isfinite(v).all() for v in values):
                self.record["allFinite"] = False
                save()
                raise ValueError("Inference returned NaN or Inf")
            if len(self.record["runMilliseconds"]) <= 3 or len(self.record["runMilliseconds"]) % 20 == 0:
                save()
            return values

    axengine.InferenceSession = MeasuredSession
    if args.task == "realesrgan":
        scale = {"x2": 2, "x4": 4}[args.variant]
        upstream = module(root / "run_axmodel.py")
        source = cv2.imread(str(root / "pics/0014.jpg"))
        if source is None:
            raise ValueError("Cannot read official sample")
        rgb = cv2.cvtColor(source, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        tensor = upstream.pre_process(rgb, 108, 10)
        start = time.perf_counter()
        result = upstream.tile_process(tensor, rgb.shape, str(root / f"model/realesrgan-{args.variant}.axmodel"), scale, 108, 10)
        pipeline_ms = (time.perf_counter() - start) * 1000
        expected = (source.shape[0] * scale, source.shape[1] * scale, 3)
        if result.shape != expected or not np.isfinite(result).all():
            raise ValueError(f"Invalid output: {result.shape}, expected {expected}")
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out / "input.png"), source)
        cv2.imwrite(str(out / "output.png"), result)
        report["results"].append({"inputShape": list(source.shape), "outputShape": list(result.shape),
                                  "scale": scale, "tilePipelineMilliseconds": pipeline_ms})
    elif args.task == "rf-detr":
        upstream = module(root / "src/infer.py")
        session = MeasuredSession(str(root / "onnx/detr.axmodel"))
        meta = session.get_inputs()[0]
        layout = "NCHW" if meta.shape[1] == 3 else "NHWC"
        height, width = meta.shape[2:4] if layout == "NCHW" else meta.shape[1:3]
        tensor, raw, transform = upstream.preprocess(str(root / "asserts/test.jpg"), height, width, layout, np.dtype(meta.dtype), False)
        detections = []
        for _ in range(3):
            values = session.run(None, {meta.name: tensor})
            decoded = upstream.decode(values, transform, 0.3)
            detections.append([{"box": box.tolist(), "score": score, "classId": label,
                                "label": upstream.CLASS_NAME_BY_ID.get(label, f"obj_{label}")}
                               for box, score, label, _ in decoded])
        raw.save(out / "input.png")
        upstream.draw(raw, decoded, str(out / "output.png"))
        report["results"] = [{"threshold": 0.3, "repeats": detections}]
    elif args.task == "rf-detr-b2":
        from PIL import Image
        import onnxruntime
        assert args.variant in ["small", "large"]
        upstream = module(root / "src/infer/b2_infer_axmodel.py")
        session = MeasuredSession(str(root / f"models/rf-detr-{args.variant}.axmodel"))
        post_file = {"small": "rfdetr_small_512_b2_post.onnx", "large": "rf-detr-large_704_b2_post.onnx"}[args.variant]
        cpu_options = onnxruntime.SessionOptions()
        cpu_options.intra_op_num_threads = 2
        cpu_options.inter_op_num_threads = 1
        post = onnxruntime.InferenceSession(str(root / "models" / post_file), sess_options=cpu_options, providers=["CPUExecutionProvider"])
        report["hostPostprocessing"] = {"file": "models/" + post_file, "provider": "CPUExecutionProvider", "purpose": "Official bbox head only; backbone and class logits run on the card."}
        names = [item.name for item in session.get_outputs()]
        for source in sorted((root / "datasets/coco2017val_5000").glob("*.jpg")):
            tensor, _ = upstream.preprocess(str(source))
            meta = session.get_inputs()[0]
            assert list(tensor.shape) == list(meta.shape) and tensor.dtype == np.dtype(meta.dtype)
            repeats, post_ms = [], []
            for _ in range(3):
                values = session.run(names, {meta.name: tensor})
                started = time.perf_counter()
                logits, boxes = upstream.run_bbox_postproc(post, names, values)
                post_ms.append((time.perf_counter() - started) * 1000)
                assert np.isfinite(logits).all() and np.isfinite(boxes).all()
                scores = upstream._sigmoid(logits[0])
                labels = scores.argmax(axis=-1)
                best = scores[np.arange(len(labels)), labels]
                keep = (best >= 0.5) & (labels > 0)
                xyxy = upstream._cxcywh_to_xyxy(boxes[0])
                repeats.append([{"classId": int(label), "label": upstream.COCO_CLASSES[int(label)], "score": float(score), "normalizedBox": box.tolist()}
                                for label, score, box in zip(labels[keep], best[keep], xyxy[keep])])
            original = Image.open(source).convert("RGB")
            original.save(out / (source.stem + "-input.png"))
            upstream.draw_detections(original.copy(), logits[0], boxes[0], 0.5).save(out / (source.stem + "-output.png"))
            report["results"].append({"input": source.relative_to(root).as_posix(), "threshold": 0.5, "repeats": repeats,
                                      "hostPostMilliseconds": post_ms, "repeatedDetectionsEqual": repeats[0] == repeats[1] == repeats[2]})
    elif args.task == "deimv2":
        from PIL import Image
        import torch
        upstream = module(root / "axmodel_inf.py")
        session = MeasuredSession(str(root / "deimv2_dinov3_s_coco.axmodel"))
        original = Image.open(root / "people.jpg").convert("RGB")
        meta = session.get_inputs()[0]
        size = meta.shape[2]
        resized, ratio, pad_w, pad_h = upstream.resize_with_aspect_ratio(original, size)
        # The pinned model card uses -ms n: ToTensor without mean/std normalization.
        tensor = upstream.T.ToTensor()(resized).unsqueeze(0).numpy()
        assert list(tensor.shape) == list(meta.shape) and tensor.dtype == np.dtype(meta.dtype)
        post = upstream.PostProcessor().deploy()
        repeats = []
        for _ in range(3):
            values = session.run(None, {meta.name: tensor})
            labels, boxes, scores = [v.numpy() for v in post({"pred_logits": torch.from_numpy(values[0]), "pred_boxes": torch.from_numpy(values[1])}, torch.tensor([[size, size]]))]
            keep = scores[0] > 0.4
            repeats.append([{"classId": int(label), "score": float(score), "box": ((box - np.array([pad_w, pad_h, pad_w, pad_h])) / ratio).tolist()}
                            for label, score, box in zip(labels[0][keep], scores[0][keep], boxes[0][keep])])
        original.save(out / "input.png")
        upstream.draw([original.copy()], labels, boxes, scores, [ratio], [(pad_w, pad_h)])[0].save(out / "output.png")
        report["results"] = [{"input": "people.jpg", "threshold": 0.4, "modelSizeArgument": "n", "repeats": repeats,
                               "repeatedDetectionsEqual": repeats[0] == repeats[1] == repeats[2]}]
    elif args.task == "visdrone":
        import hashlib
        import ctypes
        import ctypes.util
        # The pinned SDK library leaves its OpenCV symbols to its caller.
        # Python's cv2 module does not export the system C++ ABI globally.
        native_opencv = []
        for name in ["opencv_core", "opencv_imgproc", "opencv_imgcodecs"]:
            library = ctypes.util.find_library(name)
            if not library:raise RuntimeError(f"Missing system C++ library: {name}; install libopencv-dev")
            native_opencv.append(ctypes.CDLL(library, mode=ctypes.RTLD_GLOBAL))
        sys.path.insert(0, str(root / "python"))
        from visdrone_yolov26s_sdk.pydet import AXDet, ModelType
        from visdrone_yolov26s_sdk.pydet import pyaxdev
        from visdrone_yolov26s_sdk.preprocess import preprocess_image
        from visdrone_yolov26s_sdk.postprocess import draw_detections
        pyaxdev.lib_paths = [str(root / "cpp/lib/libdet.so")]
        metadata = json.loads((root / "models/model_meta.json").read_text())
        assert metadata["num_classes"] == 11 and len(metadata["classes"]) == 11
        pyaxdev.sys_init(pyaxdev.AxDeviceType.axcl_device, 0)
        detector = None
        report["provider"] = "AXCL C++"
        report["librarySha256"] = hashlib.sha256((root / "cpp/lib/libdet.so").read_bytes()).hexdigest()
        report["nativeOpenCV"] = [lib._name for lib in native_opencv]
        timing = {"model": "models/model.axmodel", "runMilliseconds": [], "allFinite": True,
                  "finiteCheckScope": "Decoded candidate boxes and scores returned by libdet; raw NPU tensors are not exposed."}
        report["sessions"] = [timing]
        try:
            detector = AXDet(str(root / "models/model.axmodel"), ModelType.ax_det_model_type_yolo11,
                             num_classes=11, threshold=0.25, mean=[0, 0, 0], std=[1 / 255] * 3,
                             dev_type=pyaxdev.AxDeviceType.axcl_device, devid=0)
            for source in sorted((root / "demo").glob("demo_*.jpg")):
                tensor = preprocess_image(str(source), target_size=640)
                repeats = []
                for _ in range(3):
                    start = time.perf_counter()
                    objects = detector.detect(tensor)
                    timing["runMilliseconds"].append((time.perf_counter() - start) * 1000)
                    assert all(0 <= obj.label < 11 and np.isfinite(obj.score) and all(np.isfinite(obj.box)) for obj in objects)
                    repeats.append([{"classId": obj.label, "label": metadata["classes"][obj.label], "score": obj.score, "box": obj.box} for obj in objects])
                # The pinned preprocessing function already returns BGR.
                bgr = tensor.copy()
                cv2.imwrite(str(out / (source.stem + "-input.png")), bgr)
                draw_detections(bgr, objects, threshold=0.25)
                cv2.imwrite(str(out / (source.stem + "-output.png")), bgr)
                report["results"].append({"input": source.relative_to(root).as_posix(), "threshold": 0.25, "repeats": repeats,
                                          "repeatedDetectionsEqual": repeats[0] == repeats[1] == repeats[2], "resultCapacity": 64})
        finally:
            if detector is not None:del detector
            pyaxdev.sys_deinit(pyaxdev.AxDeviceType.axcl_device, 0)
    elif args.task == "yolov5-seg":
        import hashlib
        import re
        import subprocess
        assert args.binary and args.binary.is_file()
        command = [str(args.binary), "-m", str(root / "ax650/yolov5s-seg.axmodel"), "-i", str(root / "football.jpg"), "-r", "3"]
        proc = subprocess.run(command, cwd=out, capture_output=True, text=True, timeout=90)
        (out / "native.log").write_text(proc.stdout + proc.stderr)
        assert proc.returncode == 0
        timing = re.search(r"Repeat (\d+) times, avg time ([\d.]+) ms, max_time ([\d.]+) ms, min_time ([\d.]+) ms", proc.stdout)
        count = re.search(r"detection num: (\d+)", proc.stdout)
        assert timing and count and (out / "yolov5s_seg_out.jpg").is_file()
        output = cv2.imread(str(out / "yolov5s_seg_out.jpg"))
        source = cv2.imread(str(root / "football.jpg"))
        assert output is not None and output.shape == source.shape
        cv2.imwrite(str(out / "input.png"), source)
        cv2.imwrite(str(out / "output.png"), output)
        report["provider"] = "AXCL C++"
        report["binarySha256"] = hashlib.sha256(args.binary.read_bytes()).hexdigest()
        report["sessions"] = [{"model": "ax650/yolov5s-seg.axmodel", "runMilliseconds": [],
                               "nativeTiming": {"repeat": int(timing[1]), "averageMilliseconds": float(timing[2]), "maxMilliseconds": float(timing[3]), "minMilliseconds": float(timing[4]), "warmup": 5}}]
        report["results"] = [{"input": "football.jpg", "detections": int(count[1]), "threshold": 0.45, "nmsThreshold": 0.45}]
    elif args.task == "dinov3":
        upstream = module(root / "scripts/infer_dinov3_backbone_axmodel.py")
        weight = "models-ax650/dinov3-vits16-pretrain-lvd1689m.axmodel"
        session = MeasuredSession(str(root / weight))
        meta = session.get_inputs()[0]
        vectors = []
        for index, name in enumerate(["ILSVRC2012_val_00000001.jpeg", "ILSVRC2012_val_00000005.jpeg", "ILSVRC2012_val_00000001.jpeg"], start=1):
            tensor = upstream.preprocess_image(root / "examples" / name, list(meta.shape))
            values = session.run(None, {meta.name: tensor})
            pool = next(v for v in values if v.ndim == 2 and v.shape[0] == 1)
            vector = pool.reshape(-1)
            vectors.append(vector.copy())
            vector_file = f"{index:02d}-{Path(name).stem}.npy"
            np.save(out / vector_file, vector, allow_pickle=False)
            shutil.copy2(root / "examples" / name, out / name)
            report["results"].append({"input": name, "vectorFile": vector_file, "dimensions": int(vector.size), "norm": float(np.linalg.norm(vector)), "first8": vector[:8].tolist()})
        if any(not np.isfinite(v).all() or np.linalg.norm(v) <= 0 for v in vectors):
            raise ValueError("DINOv3 returned nonfinite or zero-norm embeddings")
        cosine = lambda a, b: float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        report["cosine"] = {"differentImages": cosine(vectors[0], vectors[1]), "repeatedImage": cosine(vectors[0], vectors[2])}
        report["repeatComparison"] = {"elementwiseEqual": bool(np.array_equal(vectors[0], vectors[2])),
                                      "maxAbsDifference": float(np.max(np.abs(vectors[0] - vectors[2])))}
    elif args.task == "mobileclip":
        import torch
        from torchvision import transforms
        from PIL import Image
        tokenizer = module(root / "tokenizer.py").SimpleTokenizer(context_length=77)
        transform = transforms.Compose([transforms.Resize(256, interpolation=transforms.InterpolationMode.BILINEAR), transforms.CenterCrop(256), transforms.ToTensor()])
        tensor = transform(Image.open(root / "zebra.jpg").convert("RGB")).unsqueeze(0).numpy()
        texts = ["a zebra", "a dog", "two zebras"]
        tokens = tokenizer(texts).to(torch.int32).numpy()
        image_session = MeasuredSession(str(root / f"mobileclip2_{args.variant}/AX650/mobileclip2_{args.variant}_image_encoder.axmodel"))
        image_vector = image_session.run(None, {image_session.get_inputs()[0].name: tensor})[0]
        del image_session
        text_session = MeasuredSession(str(root / f"mobileclip2_{args.variant}/AX650/mobileclip2_{args.variant}_text_encoder.axmodel"))
        meta = text_session.get_inputs()[0]
        if meta.shape[0] == len(texts):
            text_vectors = text_session.run(None, {meta.name: np.asarray(tokens, dtype=meta.dtype)})[0]
        elif meta.shape[0] == 1:
            text_vectors = np.concatenate([text_session.run(None, {meta.name: np.asarray(t[None], dtype=meta.dtype)})[0] for t in tokens])
        else:
            raise ValueError(f"Unsupported text batch shape: {meta.shape}")
        image_vector = image_vector / np.linalg.norm(image_vector, axis=-1, keepdims=True)
        text_vectors = text_vectors / np.linalg.norm(text_vectors, axis=-1, keepdims=True)
        similarities = (image_vector @ text_vectors.T)[0]
        logits = similarities * 100
        probabilities = np.exp(logits - logits.max()) / np.exp(logits - logits.max()).sum()
        report["results"] = [{"text": text, "cosine": float(sim), "probabilityWithinCandidates": float(prob)} for text, sim, prob in zip(texts, similarities, probabilities)]
        shutil.copy2(root / "zebra.jpg", out / "input.jpg")
    elif args.task == "siglip2":
        from transformers import AutoTokenizer, SiglipImageProcessor, SiglipProcessor
        from PIL import Image
        # This fixed repository supplies tokenizer.json, not tokenizer.model.
        tokenizer = AutoTokenizer.from_pretrained(str(root / "tokenizer"), local_files_only=True, use_fast=True)
        image_processor = SiglipImageProcessor.from_pretrained(str(root / "tokenizer"), local_files_only=True)
        processor = SiglipProcessor(image_processor=image_processor, tokenizer=tokenizer)
        texts = ["a photo of 2 cats", "a photo of 2 dogs"]
        inputs = processor(text=texts, images=Image.open(root / "000000039769.jpg").convert("RGB"), padding="max_length", max_length=64, truncation=True, return_tensors="np")
        vision = MeasuredSession(str(root / "ax650/siglip2-base-patch16-224_vision.axmodel"))
        image_vector = vision.run(None, {vision.get_inputs()[0].name: inputs.pixel_values})[0].copy()
        del vision
        text_session = MeasuredSession(str(root / "ax650/siglip2-base-patch16-224_text.axmodel"))
        meta = text_session.get_inputs()[0]
        vectors = np.concatenate([text_session.run(None, {meta.name: np.asarray(t[None], dtype=meta.dtype)})[0].copy() for t in inputs.input_ids])
        image_vector /= np.linalg.norm(image_vector, axis=-1, keepdims=True)
        vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
        cosines = (image_vector @ vectors.T)[0]
        logits = cosines * np.exp(4.7244534) - 16.771725
        probs = 1 / (1 + np.exp(-logits))
        report["results"] = [{"text": text, "cosine": float(cosine), "sigmoidScore": float(prob)} for text, cosine, prob in zip(texts, cosines, probs)]
        shutil.copy2(root / "000000039769.jpg", out / "input.jpg")
    elif args.task == "yolov7-face":
        import re
        import subprocess
        if not args.binary or not args.binary.is_absolute():
            raise ValueError("Provide an absolute --binary path")
        command = [str(args.binary), "-m", str(root / "ax650/yolov7-face.axmodel"), "-i", str(root / "selfie.jpg"), "-r", "3"]
        result = subprocess.run(command, cwd=out, text=True, capture_output=True, timeout=120, check=True)
        print(result.stdout, flush=True)
        count = int(re.search(r'detection num:\s*(\d+)', result.stdout).group(1))
        timing = re.search(r'Repeat (\d+) times, avg time ([\d.]+) ms, max_time ([\d.]+) ms, min_time ([\d.]+) ms', result.stdout)
        output = out / "yolov7_face_out.jpg"
        if not output.is_file():
            raise ValueError("Face detector did not generate an output image")
        shutil.copy2(root / "selfie.jpg", out / "input.jpg")
        report["provider"] = "AXCL C++"
        report["sessions"] = [{"model": "ax650/yolov7-face.axmodel", "runMilliseconds": [],
                               "nativeTiming": {"repeat": int(timing[1]), "averageMilliseconds": float(timing[2]), "maxMilliseconds": float(timing[3]), "minMilliseconds": float(timing[4])}}]
        report["results"] = [{"detections": count, "scoreThreshold": .2, "nmsThreshold": .5}]
    elif args.task == "mixformer":
        from PIL import Image
        upstream = module(root / "run_mixformer2_axmodel.py")
        tracker = upstream.MFTrackerORT(str(root / "ax650/mixformer_v2.axmodel"))
        cap = cv2.VideoCapture(str(root / "car.avi"))
        frames = []
        for index in range(61):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Video ended at frame {index}")
            if index == 0:
                cv2.imwrite(str(out / "input.png"), frame)
                tracker.track_init(frame, [1079, 482], [99, 106])
                continue
            state = tracker.track(frame)
            bbox = np.asarray(state["target_bbox"])
            if not np.isfinite(bbox).all() or min(bbox[2:]) <= 0:
                raise ValueError("Invalid tracking box")
            report["results"].append({"frame": index, "bbox": bbox.tolist(), "score": float(np.asarray(state["conf_score"]).item())})
            if index in [1, 30, 60]:
                cv2.imwrite(str(out / f"frame-{index:03d}.png"), frame)
            if index % 2 == 0:
                preview = cv2.resize(frame, (768, int(frame.shape[0] * 768 / frame.shape[1])))
                frames.append(Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        frames[0].save(out / "tracking.gif", save_all=True, append_images=frames[1:], duration=round(2000 / fps), loop=0)
        report["sourceFps"] = fps
        report["initialBox"] = [1079, 482, 99, 106]
    elif args.task == "super-resolution":
        weights = {"edsr": "edsr_baseline_x2_1.axmodel", "edsr-2k": "edsr_baseline_x2_2k.axmodel", "espcn": "espcn_x2_T9.axmodel", "espcn-2k": "espcn_x2_T9_2k.axmodel"}
        session = MeasuredSession(str(root / "model_convert/axmodel" / weights[args.variant]))
        meta = session.get_inputs()[0]
        cap = cv2.VideoCapture(str(root / "video/test_1920x1080.mp4"))
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise ValueError("Cannot read first video frame")
        height, width = meta.shape[2:4]
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / "input.png"), frame)
        if args.variant.startswith("edsr"):
            # Upstream EDSR demonstration keeps OpenCV's BGR channel order and range 0..255.
            tensor = np.ascontiguousarray(frame.transpose(2, 0, 1)[None], dtype=meta.dtype)
            for _ in range(3):
                sr = session.run(None, {meta.name: tensor})[0]
            result = np.round(np.clip(sr, 0, 255))[0].transpose(1, 2, 0).astype(np.uint8)
        else:
            imgproc = module(root / "python/imgproc.py")
            tensor, cb, cr = imgproc.preprocess_one_frame(frame)
            for _ in range(3):
                sr = session.run(None, {meta.name: tensor})[0]
            y = imgproc.array_to_image(sr).astype(np.float32) / 255
            cb = cv2.resize(cb, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
            cr = cv2.resize(cr, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
            result = np.clip(imgproc.ycbcr_to_bgr(cv2.merge([y[:, :, 0], cb, cr])) * 255, 0, 255).astype(np.uint8)
        if result.shape != (height * 2, width * 2, 3):
            raise ValueError(f"Invalid SR output: {result.shape}")
        cv2.imwrite(str(out / "output.png"), result)
        report["results"] = [{"inputShape": list(frame.shape), "outputShape": list(result.shape), "sourceFrame": 0, "scale": 2}]
    elif args.task == "satrn":
        image = cv2.imread(str(root / "demo_text_recog.jpg"))
        if image is None:
            raise ValueError("Cannot read OCR sample")
        resized = cv2.resize(image, (100, 32), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        normalized = (resized - np.array([123.675, 116.28, 103.53], np.float32)) / np.array([58.395, 57.12, 57.375], np.float32)
        encoder = MeasuredSession(str(root / "axmodel/backbone_encoder.axmodel"))
        encoded = encoder.run(None, {encoder.get_inputs()[0].name: np.ascontiguousarray(normalized.transpose(2, 0, 1)[None])})[0]
        del encoder
        decoder = MeasuredSession(str(root / "axmodel/decoder.axmodel"))
        target = np.full((1, 26), 91, dtype=np.int32)
        target[:, 0] = 90
        alphabet = string.digits + string.ascii_lowercase + string.ascii_uppercase + '!"#$%&\'()*+,-./:;<=>?@[\\]_`~'
        assert len(alphabet) == 90
        text = ""
        tokens, scores = [], []
        for step in range(25):
            feeds = {"init_target_seq": target, "out_enc": encoded,
                     "src_mask": np.ones(encoded.shape[:2], np.float32), "step": np.array([step], np.int32)}
            feeds = {v.name: np.asarray(feeds[v.name], dtype=v.dtype) for v in decoder.get_inputs()}
            logits = decoder.run(None, feeds)[0].reshape(-1)
            probs = np.exp(logits - logits.max()) / np.exp(logits - logits.max()).sum()
            token = int(np.argmax(logits))
            target[:, step + 1] = token
            tokens.append(token)
            scores.append(float(probs[token]))
            if token == 90:
                break
            if token < len(alphabet):
                text += alphabet[token]
        report["results"] = [{"text": text, "tokenIds": tokens, "tokenScores": scores, "ended": tokens[-1] == 90}]
        cv2.imwrite(str(out / "input.png"), image)
    elif args.task == "silero-vad":
        import wave
        upstream = module(root / "silero_sdk/silero_vad_axera/SileroAx.py")
        detector = upstream.SileroAx(str(root / "models/silero_vad_ax650.axmodel"), providers=["AXCLRTExecutionProvider"])
        with wave.open(str(root / "demo.wav"), "rb") as wav:
            sr, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
            if (sr, channels, width) != (16000, 1, 2):
                raise ValueError(f"Expected 16kHz mono PCM16, got {(sr, channels, width)}")
            raw = wav.readframes(wav.getnframes())
        audio = np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768
        probabilities, segments = [], []
        start, silence_start = None, None
        for offset in range(0, len(audio), 512):
            chunk = audio[offset:offset + 512]
            chunk = np.pad(chunk, (0, 512 - len(chunk)))
            probability = float(detector(chunk, sr).item())
            probabilities.append(probability)
            if probability >= .5:
                if start is None:
                    start = offset
                silence_start = None
            elif start is not None:
                if silence_start is None:
                    silence_start = offset
                if offset + 512 - silence_start >= 3200:
                    if silence_start - start >= 4000:
                        segments.append([start, silence_start])
                    start, silence_start = None, None
        if start is not None:
            end = silence_start if silence_start is not None else len(audio)
            if end - start >= 4000:
                segments.append([start, end])
        for index, (start, end) in enumerate(segments):
            with wave.open(str(out / f"segment-{index + 1:02d}.wav"), 'wb') as wav:
                wav.setparams((1, 2, sr, 0, 'NONE', 'not compressed'))
                wav.writeframes(raw[start * 2:end * 2])
        shutil.copy2(root / "demo.wav", out / "input.wav")
        report["results"] = [{"audioSeconds": len(audio) / sr, "frameMilliseconds": 32, "threshold": .5,
                              "minSpeechMilliseconds": 250, "minSilenceMilliseconds": 200,
                              "segments": [{"start": a / sr, "end": b / sr} for a, b in segments], "probabilities": probabilities}]
    report["completed"] = True
    save()
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
