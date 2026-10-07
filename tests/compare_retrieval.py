"""Developer-selected regressions; does not call or evaluate any dialogue model."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/nolan-director'
BEFORE=ROOT/'validation/retrieval-before'

CASES=[
    ('多线混乱','为什么我的两条线来回切，观众越来越糊涂？',['V4-N001','V4-N003','J01']),
    ('人物距离','我的画面很漂亮，但感觉离这个人很远。',['N01','K03','EXP-ASC01']),
    ('缺钱','没有钱拍大场面，你以前怎么处理？',['V4-N004','QA12-I06','K16','EXP-ASC02']),
    ('追加表演','演员老想再来一条，我觉得已经够了。',['QA12-D02','VE03']),
    ('解释过量','这段台词都说明白了，但好像更难懂了。',['VE02','V4-N006']),
    ('合作改变','给我讲一个拍片时改变最初想法的经验。',['QA12-D02','QA12-I09']),
    ('设备限制','设备太少，就我们几个人能拍出什么？',['V4-N004','K16','DCA12']),
    ('切换理解','这几段来回切，故事看不懂了。',['V4-N001','J01','K01']),
    ('漂亮而疏离','房间拍得好看，却让人物很疏离。',['N01','K03','EXP-ASC01']),
    ('准备方式','两个人准备方法不一样，要统一排练吗？',['QA12-D01','K11','J16']),
    ('声音','配乐一响就很煽情，我又不想全去掉。',['QA12-DB02','K10','DCA09']),
    ('画外世界','在一个房间里，怎么让观众感到外面的世界很大？',['K05','DCA10','EXP-DGA12A']),
]

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def run():
    old=module(BEFORE/'recall.py','old_recall')
    new=module(SKILL/'scripts/recall.py','new_recall')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='nolan_compare_') as tmp:
        same=Path(tmp);(same/'assets').mkdir();(same/'references').mkdir()
        shutil.copyfile(BEFORE/'assets/library.json',same/'assets/library.json')
        shutil.copyfile(SKILL/'references/situations.json',same/'references/situations.json')
        for label,query,expected in CASES:
            row={'case':label,'query':query,'expected_any':expected}
            for name,func,root in [('before',old.recall,BEFORE),('new_retriever_same_corpus',new.recall,same),('new_retriever_refined_corpus',new.recall,SKILL)]:
                result=func(query,root=root,backend='json',budget=16000,limit=4)
                ids=[c['id'] for c in result['cards']]
                row[name]={'top4':ids,'hit':bool(set(ids).intersection(expected))}
            rows.append(row)
    report={'status':'executed','scope':'developer-selected retrieval regressions, not held-out evaluation or model response quality',
            'cases':len(rows),'top4_hit_counts':{key:sum(r[key]['hit'] for r in rows) for key in ('before','new_retriever_same_corpus','new_retriever_refined_corpus')},
            'generated_dialogue_evaluated':False,'results':rows}
    (ROOT/'validation/retrieval-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    run()
