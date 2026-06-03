import os
import json
from dotenv import load_dotenv
from flask import Flask, request, Response
from flask_cors import CORS
from groq import Groq

from agent.basic_agent import get_current_time, calculate, get_weather, analyze_text
from agent.memory import save_memory, recall_memory

load_dotenv()

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

AVAILABLE_FUNCTIONS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "get_weather": get_weather,
    "analyze_text": analyze_text,
    "save_memory": save_memory,
    "recall_memory": recall_memory,
}

TOOLS = [
    {"type": "function", "function": {"name": "get_current_time", "description": "Returns the current date and time.", "parameters": {"type": "object", "properties": {"timezone": {"type": "string", "description": "Timezone like 'UTC', 'Asia/Tokyo'."}}, "required": []}}},
    {"type": "function", "function": {"name": "calculate", "description": "Evaluates a mathematical expression safely.", "parameters": {"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression like '2 + 3 * 4'."}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Gets a simulated weather report for a city.", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City name."}, "unit": {"type": "string", "description": "'celsius' or 'fahrenheit'."}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "analyze_text", "description": "Analyzes text and returns statistics.", "parameters": {"type": "object", "properties": {"text": {"type": "string", "description": "The text to analyze."}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "save_memory", "description": "Saves a piece of information to long-term memory.", "parameters": {"type": "object", "properties": {"key": {"type": "string", "description": "Category (e.g., 'user_name')."}, "value": {"type": "string", "description": "The information to remember."}}, "required": ["key", "value"]}}},
    {"type": "function", "function": {"name": "recall_memory", "description": "Searches long-term memory for a topic.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Topic to search for."}}, "required": ["query"]}}}
]

SYSTEM_PROMPT = """You are a highly advanced AI assistant with long-term memory and local tools.
RULES:
1. For time/date -> use get_current_time
2. For math -> use calculate
3. For weather -> use get_weather
4. For text analysis -> use analyze_text
5. If user tells personal facts (e.g., "My name is John"), use `save_memory`.
6. If user asks about past info (e.g., "What is my name?"), use `recall_memory`.
7. NEVER guess personal details. Check memory first.
8. Keep responses concise.
"""

@app.route("/")
def index():
    return Response(HTML_PAGE, content_type="text/html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    
    # Load session history (simple in-memory for web)
    session_id = data.get("session_id", "default")
    if not hasattr(chat, 'sessions'):
        chat.sessions = {}
    if session_id not in chat.sessions:
        chat.sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    messages = chat.sessions[session_id]
    messages.append({"role": "user", "content": user_message})

    def event_generator():
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            msg = response.choices[0].message

            while msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    tool_type = "memory" if "memory" in func_name else "tool"
                    
                    yield f"event: tool_call\ndata: {json.dumps([{'name': func_name, 'args': func_args, 'type': tool_type}])}\n\n"

                    func_to_call = AVAILABLE_FUNCTIONS[func_name]
                    result = str(func_to_call(**func_args))
                    
                    yield f"event: tool_result\ndata: {json.dumps([{'name': func_name, 'result': result, 'type': tool_type}])}\n\n"

                    messages.append(msg)
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    tools=TOOLS
                )
                msg = response.choices[0].message

            if msg.content:
                yield f"event: response\ndata: {json.dumps({'text': msg.content})}\n\n"
                messages.append({"role": "assistant", "content": msg.content})

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            messages.pop() # Remove failed user message

        yield "event: done\ndata: {}\n\n"

    return Response(event_generator(), content_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ADK Advanced Agent</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700;900&display=swap" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>
:root{--bg:#0a0e17;--bg2:#111827;--card:#1a2236;--fg:#e8ecf4;--muted:#7a8ba8;--accent:#00e89d;--accent-dim:rgba(0,232,157,.12);--accent-glow:rgba(0,232,157,.3);--tool:#f59e0b;--tool-dim:rgba(245,158,11,.12);--memory:#c084fc;--memory-dim:rgba(192,132,252,.12);--search:#38bdf8;--search-dim:rgba(56,189,248,.12);--err:#ef4444;--border:#1e293b;--border2:#2a3a52;--rad:12px;--mono:'JetBrains Mono',monospace;--ui:'DM Sans',sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:var(--ui);min-height:100vh;overflow:hidden}
.bg-layer{position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(ellipse 600px 400px at 15% 20%,rgba(0,232,157,.06),transparent),radial-gradient(ellipse 500px 500px at 85% 80%,rgba(59,130,246,.05),transparent)}
.bg-grid{position:fixed;inset:0;z-index:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.015) 1px,transparent 1px);background-size:60px 60px;animation:gs 30s linear infinite}
@keyframes gs{to{transform:translate(60px,60px)}}
.app{position:relative;z-index:1;display:flex;flex-direction:column;height:100vh;max-width:860px;margin:0 auto;padding:0 16px}
.header{display:flex;align-items:center;justify-content:space-between;padding:20px 0 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.header-left{display:flex;align-items:center;gap:14px}
.avatar{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,var(--accent),#00b87a);display:flex;align-items:center;justify-content:center;font-size:20px;color:#000;font-weight:900;box-shadow:0 0 20px var(--accent-glow);animation:ap 3s ease-in-out infinite}
@keyframes ap{0%,100%{box-shadow:0 0 20px var(--accent-glow)}50%{box-shadow:0 0 30px var(--accent-glow),0 0 60px rgba(0,232,157,.1)}}
.htitle{font-size:20px;font-weight:900;letter-spacing:-.5px}
.hsub{font-size:12px;color:var(--muted);margin-top:2px;font-family:var(--mono)}
.badge{display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:20px;background:var(--accent-dim);border:1px solid rgba(0,232,157,.2);font-size:12px;color:var(--accent);font-weight:500}
.bdot{width:7px;height:7px;border-radius:50%;background:var(--accent);animation:db 2s ease-in-out infinite}
@keyframes db{0%,100%{opacity:1}50%{opacity:.3}}
.messages{flex:1;overflow-y:auto;padding:24px 0;display:flex;flex-direction:column;gap:8px;scroll-behavior:smooth}
.messages::-webkit-scrollbar{width:5px}
.messages::-webkit-scrollbar-thumb{background:var(--border2);border-radius:10px}
.msg{display:flex;gap:12px;max-width:85%;animation:mi .3s ease-out}
@keyframes mi{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.msg.user{align-self:flex-end;flex-direction:row-reverse}
.mav{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;margin-top:4px}
.msg.agent .mav{background:var(--accent-dim);color:var(--accent)}
.msg.user .mav{background:rgba(59,130,246,.15);color:#60a5fa}
.mbody{padding:12px 16px;border-radius:var(--rad);line-height:1.65;font-size:14.5px}
.msg.agent .mbody{background:var(--card);border:1px solid var(--border);border-top-left-radius:4px}
.msg.user .mbody{background:linear-gradient(135deg,#1e3a5f,#1a2e4a);border:1px solid rgba(59,130,246,.2);border-top-right-radius:4px}
.mbody pre{background:rgba(0,0,0,.3);padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0;font-family:var(--mono);font-size:12.5px;line-height:1.5}
.mbody code{font-family:var(--mono);font-size:13px;background:rgba(0,232,157,.08);padding:2px 6px;border-radius:4px;color:var(--accent)}
.mbody p{margin-bottom:8px}.mbody p:last-child{margin-bottom:0}
.mbody strong{color:var(--accent);font-weight:700}
.ti{display:flex;align-items:center;gap:10px;padding:10px 16px;margin:4px 0 4px 44px;border-radius:8px;font-size:13px;animation:ts .3s ease-out;font-family:var(--mono)}
@keyframes ts{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:translateX(0)}}
.ti.tool{background:var(--tool-dim);border:1px solid rgba(245,158,11,.15);color:var(--tool)}
.ti.memory{background:var(--memory-dim);border:1px solid rgba(192,132,252,.15);color:var(--memory)}
.ti i{font-size:14px}.ti .tn{font-weight:700}.ti .ta{color:var(--muted);font-size:11.5px;margin-left:auto;max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tri{display:flex;align-items:flex-start;gap:10px;padding:10px 16px;margin:2px 0 2px 44px;border-radius:8px;font-size:12px;color:var(--muted);font-family:var(--mono);animation:ts .3s ease-out;max-height:120px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
.tri.tool{background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.1)}
.tri.memory{background:rgba(192,132,252,.06);border:1px solid rgba(192,132,252,.1)}
.tri i{margin-top:2px;flex-shrink:0}
.tri.tool i{color:var(--tool)}.tri.memory i{color:var(--memory)}
.typing{display:none;align-items:center;gap:10px;padding:12px 16px;margin:4px 0 4px 44px;color:var(--muted);font-size:13px}
.typing.show{display:flex}
.td{display:flex;gap:4px}
.td span{width:6px;height:6px;border-radius:50%;background:var(--muted);animation:tb 1.2s ease-in-out infinite}
.td span:nth-child(2){animation-delay:.15s}.td span:nth-child(3){animation-delay:.3s}
@keyframes tb{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-6px);opacity:1}}
.input-area{padding:16px 0 24px;border-top:1px solid var(--border);flex-shrink:0}
.iw{display:flex;align-items:flex-end;gap:10px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:8px 8px 8px 18px;transition:border-color .2s,box-shadow .2s}
.iw:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-dim)}
.iw textarea{flex:1;background:none;border:none;outline:none;color:var(--fg);font-family:var(--ui);font-size:14.5px;resize:none;max-height:120px;line-height:1.5;padding:6px 0}
.iw textarea::placeholder{color:var(--muted)}
.sbtn{width:40px;height:40px;border-radius:12px;background:var(--accent);border:none;color:#000;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;flex-shrink:0}
.sbtn:hover{transform:scale(1.05);box-shadow:0 0 20px var(--accent-glow)}.sbtn:active{transform:scale(.95)}.sbtn:disabled{opacity:.3;cursor:not-allowed;transform:none;box-shadow:none}
.ihint{text-align:center;font-size:11px;color:var(--muted);margin-top:10px;opacity:.6}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;text-align:center;padding:40px 20px}
.wicon{width:72px;height:72px;border-radius:20px;background:linear-gradient(135deg,var(--accent),#00b87a);display:flex;align-items:center;justify-content:center;font-size:32px;color:#000;margin-bottom:20px;box-shadow:0 0 40px var(--accent-glow);animation:ap 3s ease-in-out infinite}
.welcome h2{font-size:26px;font-weight:900;margin-bottom:8px;letter-spacing:-.5px}
.welcome p{color:var(--muted);font-size:14.5px;max-width:480px;line-height:1.6}
.sugs{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:28px;width:100%;max-width:560px}
.sug{padding:14px 16px;border-radius:12px;background:var(--card);border:1px solid var(--border);text-align:left;cursor:pointer;transition:all .2s;font-size:13px;color:var(--fg);line-height:1.45}
.sug:hover{border-color:var(--accent);background:var(--accent-dim);transform:translateY(-2px)}
.sug .si{display:inline-block;margin-right:6px;font-size:14px;color:var(--accent)}
.sug .sl{display:block;font-weight:700;margin-bottom:2px;font-size:13.5px}
.sug .sd{color:var(--muted);font-size:11.5px}
@media(max-width:640px){.sugs{grid-template-columns:1fr}.msg{max-width:92%}.hsub{display:none}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}}
</style>
</head>
<body>
<div class="bg-layer"></div>
<div class="bg-grid"></div>
<div class="app">
  <header class="header">
    <div class="header-left">
      <div class="avatar" aria-hidden="true">A</div>
      <div><div class="htitle">Advanced Agentic AI</div><div class="hsub">Llama 3 &middot; Memory + Tools</div></div>
    </div>
    <div class="badge"><span class="bdot"></span>Online</div>
  </header>
  <div class="welcome" id="welcome">
    <div class="wicon"><i class="fas fa-brain"></i></div>
    <h2>Advanced Agentic AI</h2>
    <p>I have long-term memory and local tools. Try saving a memory and recalling it!</p>
    <div class="sugs">
      <div class="sug" onclick="useS(this)"><span class="si"><i class="fas fa-user-tag"></i></span><span class="sl">My name is Kunal</span><span class="sd">Tests Memory Save</span></div>
      <div class="sug" onclick="useS(this)"><span class="si"><i class="fas fa-calculator"></i></span><span class="sl">Calculate 50 * 432</span><span class="sd">Tests Local Tool</span></div>
      <div class="sug" onclick="useS(this)"><span class="si"><i class="fas fa-cloud-sun"></i></span><span class="sl">Weather in Tokyo</span><span class="sd">Tests Weather Tool</span></div>
      <div class="sug" onclick="useS(this)"><span class="si"><i class="fas fa-rotate-left"></i></span><span class="sl">What is my name?</span><span class="sd">Tests Memory Recall</span></div>
    </div>
  </div>
  <div class="messages" id="msgs" style="display:none"></div>
  <div class="typing" id="typing"><div class="td"><span></span><span></span><span></span></div><span>Thinking...</span></div>
  <div class="input-area">
    <div class="iw">
      <textarea id="inp" rows="1" placeholder="Ask me anything..." aria-label="Type your message"></textarea>
      <button class="sbtn" id="sbtn" aria-label="Send"><i class="fas fa-arrow-up"></i></button>
    </div>
    <div class="ihint">Press Enter to send &middot; Shift+Enter for new line</div>
  </div>
</div>
<script>
const msgsEl=document.getElementById('msgs'),welEl=document.getElementById('welcome'),typEl=document.getElementById('typing'),inpEl=document.getElementById('inp'),sbtnEl=document.getElementById('sbtn');
let sid='web-'+Math.random().toString(36).slice(2,10),busy=false,curEv='';
inpEl.addEventListener('input',()=>{inpEl.style.height='auto';inpEl.style.height=Math.min(inpEl.scrollHeight,120)+'px'});
inpEl.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});
sbtnEl.addEventListener('click',send);
function useS(el){inpEl.value=el.querySelector('.sl').textContent;inpEl.style.height='auto';inpEl.style.height=Math.min(inpEl.scrollHeight,120)+'px';send()}
function showM(){welEl.style.display='none';msgsEl.style.display='flex'}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function fmt(t){let h=esc(t);h=h.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');h=h.replace(/```\\w*\\n?([\\s\\S]*?)```/g,'<pre><code>$1</code></pre>');h=h.replace(/`([^`]+)`/g,'<code>$1</code>');h=h.split('\\n\\n').map(p=>'<p>'+p.replace(/\\n/g,'<br>')+'</p>').join('');return h}
function addU(t){showM();const d=document.createElement('div');d.className='msg user';d.innerHTML='<div class="mav"><i class="fas fa-user"></i></div><div class="mbody">'+esc(t)+'</div>';msgsEl.appendChild(d);scroll()}
function addA(t){const d=document.createElement('div');d.className='msg agent';d.innerHTML='<div class="mav"><i class="fas fa-brain"></i></div><div class="mbody">'+fmt(t)+'</div>';msgsEl.appendChild(d);scroll()}
function addTC(tools){tools.forEach(t=>{const type=t.type||'tool';const icons={memory:'fa-brain',tool:'fa-wrench'};const d=document.createElement('div');d.className='ti '+type;d.innerHTML='<i class="fas '+(icons[type]||'fa-wrench')+'"></i><span class="tn">'+t.name+'</span><span class="ta" title="'+esc(JSON.stringify(t.args))+'">'+esc(JSON.stringify(t.args))+'</span>';msgsEl.appendChild(d)});scroll()}
function addTR(res){res.forEach(r=>{const type=r.type||'tool';const icons={memory:'fa-brain',tool:'fa-check'};const d=document.createElement('div');d.className='tri '+type;d.innerHTML='<i class="fas '+(icons[type]||'fa-check')+'"></i><span>'+esc(r.result)+'</span>';msgsEl.appendChild(d)});scroll()}
function scroll(){requestAnimationFrame(()=>{msgsEl.scrollTop=msgsEl.scrollHeight})}
async function send(){const t=inpEl.value.trim();if(!t||busy)return;busy=true;sbtnEl.disabled=true;inpEl.value='';inpEl.style.height='auto';addU(t);typEl.classList.add('show');try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t,session_id:sid})});if(!r.ok)throw new Error('Server error: '+r.status);const rd=r.body.getReader(),dc=new TextDecoder();let buf='';while(true){const{done,value}=await rd.read();if(done)break;buf+=dc.decode(value,{stream:true});const lines=buf.split('\\n');buf=lines.pop()||'';for(const l of lines){if(l.startsWith('event: '))curEv=l.slice(7).trim();else if(l.startsWith('data: '))handle(JSON.parse(l.slice(6)))}}}catch(e){console.error(e);addA('Sorry, error: '+e.message)}finally{typEl.classList.remove('show');busy=false;sbtnEl.disabled=false;inpEl.focus()}}
function handle(d){switch(curEv){case'tool_call':typEl.classList.remove('show');addTC(d);typEl.classList.add('show');break;case'tool_result':addTR(d);break;case'response':typEl.classList.remove('show');addA(d.text);break;case'error':typEl.classList.remove('show');addA('Error: '+(d.error||'Unknown'));break}}
inpEl.focus();
</script>
</body>
</html>"""


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY") or "paste" in os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set in .env")
        exit(1)
    print("\n  Advanced Agent Server (Llama 3 via Groq)")
    print("  Open http://localhost:8080\n")
    app.run(host="0.0.0.0", port=8080, debug=False)