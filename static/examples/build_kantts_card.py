"""Build the fixed KAN-TTS CPU pipeline with AXCL ModelSession."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--build-dir',type=Path,required=True);a=p.parse_args();root=a.model_dir.resolve();out=a.build_dir.resolve();out.mkdir(exist_ok=False,parents=True);here=Path(__file__).resolve().parent
source=root/'sdk/src/kantts.cpp';text=source.read_text(encoding='utf-8');digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert digest=='465095488ec1da52ba83956fa7956223ec8f3fceccd0fdf44ce506ce792ae58e', 'Use the fixed official revision'
patches=[('    int T = (int)sy.size() - 1;  // 去掉末尾 ~','    int T = (int)sy.size() - 1;  // 去掉末尾 ~\n    if(T<1 || T>22) throw std::runtime_error("Each segment needs 1..22 valid symbols");\n    if(sy.size()!=tone.size() || sy.size()!=syll.size() || sy.size()!=ws.size() || sy.size()!=emo.size() || sy.size()!=spk.size()) throw std::runtime_error("Mismatched symbol categories");'),
('                reps[t] = (int)(durations[t] + 0.5f);','                if(!std::isfinite(durations[t]) || durations[t]<0 || durations[t]>810) throw std::runtime_error("Invalid predicted duration");\n                reps[t] = (int)(durations[t] + 0.5f);'),
('            int pad = 3 - sum % 3;','            if(sum<1 || sum>810) throw std::runtime_error("Duration exceeds CPU decoder capacity");\n            int pad = 3 - sum % 3;'),
('        M = (int)memory.size() / 160;','        M = (int)memory.size() / 160;\n        if(M<1 || M>270 || memory.size()%160) throw std::runtime_error("Invalid decoder memory");')]
for before,after in patches:assert text.count(before)==1; text=text.replace(before,after)
(out/'kantts.cpp').write_text(text,encoding='utf-8');cmd=['g++','-O3','-march=armv8-a','-std=c++17','-I'+str(root/'sdk/include'),'-I/usr/include/axcl',str(here/'kantts_axcl.cpp'),str(out/'kantts.cpp'),str(here/'kantts_main.cpp'),'-L/usr/lib/axcl','-Wl,-rpath,/usr/lib/axcl','-laxcl_rt','-lpthread','-o',str(out/'kantts_card')]
subprocess.run(cmd,check=True);report={'officialSourceSha256':digest,'adaptedSourceSha256':hashlib.sha256((out/'kantts.cpp').read_bytes()).hexdigest(),'command':cmd,'patches':[b for b,_ in patches],'binarySha256':hashlib.sha256((out/'kantts_card').read_bytes()).hexdigest()};(out/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
