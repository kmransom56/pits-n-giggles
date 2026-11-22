import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=[("Direct · tiny.en",0.6,0.35,0.12,0,0.19),("Direct · base.en",0.6,0.61,0.12,0,0.19),("Direct · small.en (default)",0.6,1.82,0.12,0,0.19),
("Complex · 3B, reordered prompt",0.6,1.82,0.14,4.9,0.19),("Complex · 3B, current prompt",0.6,1.82,0.14,7.6,0.19),("Complex · 8B (default), current prompt",0.6,1.82,0.14,18.5,0.19)]
segs=["End-of-speech pause","Whisper STT","MCP telemetry collect","LLM card selector","Piper first audio"]
cols=["#9aa5b1","#2f6f9f","#4f9d69","#c8553d","#e0a458"]
fig,ax=plt.subplots(figsize=(10,4.6),dpi=150)
for i,r in enumerate(rows):
    left=0
    for j,v in enumerate(r[1:]):
        ax.barh(i,v,left=left,color=cols[j],label=segs[j] if i==0 else None,edgecolor="white",linewidth=0.5); left+=v
    ax.text(left+0.2,i,f"{left:.1f} s",va="center",fontsize=9)
ax.axvline(0.6+1.82+0.14+8.0,color="#c8553d",ls="--",lw=1); ax.text(10.7,5.45,"8 s selector budget ends\n(answer refused)",fontsize=8,color="#c8553d",va="top")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows],fontsize=9); ax.invert_yaxis()
ax.set_xlabel("Seconds from end of question to first audio (2 vCPU Xeon 2.9 GHz, CPU only)",fontsize=9)
ax.set_title("Measured voice-path latency budget",fontsize=11,loc="left")
ax.legend(fontsize=8,ncol=5,loc="lower center",bbox_to_anchor=(0.5,-0.32),frameon=False)
ax.spines[["top","right"]].set_visible(False); ax.set_xlim(0,24)
plt.tight_layout(); plt.savefig(str(__import__("pathlib").Path(__file__).resolve().parents[2]/"docs"/"architecture-audit"/"voice_latency_budget.png"),bbox_inches="tight")
