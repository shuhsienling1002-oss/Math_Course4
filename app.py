import streamlit as st
import random
import uuid
from dataclasses import dataclass, field
from typing import List

# ==========================================
# 0. 全局設定 & 跨平台適配
# ==========================================
MAX_LEVEL = 10

st.set_page_config(
    page_title="整數極限：向量超頻",
    page_icon="🚀",
    layout="wide",  # 改為 wide 以適配手機全寬
    initial_sidebar_state="collapsed"
)

# ==========================================
# 1. 核心配置與 Mobile-First CSS
# ==========================================
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<style>
    /* --- 全局重置 --- */
    .stApp { background-color: #020617; color: #f8fafc; }
    
    /* 隱藏 Streamlit 預設元素以模擬 APP */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* --- 容器適配 --- */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important; /* 預留底部操作區 */
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 800px; /* 平板以上限制寬度 */
        margin: 0 auto;
    }

    /* --- 向量儀表板 (手機版優化) --- */
    .vector-scope {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 15px 10px;
        margin: 10px 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        position: relative;
        overflow: hidden;
        min-height: 140px;
    }

    /* --- 數線系統 --- */
    .number-line {
        width: 100%; height: 2px; background: #475569;
        position: relative; margin: 25px 0;
    }
    .center-mark {
        position: absolute; left: 50%; top: -8px;
        width: 2px; height: 18px; background: #ffffff; z-index: 5;
    }
    .flip-indicator {
        font-size: 0.8rem; color: #facc15; font-weight: bold;
        text-align: center; margin-top: 8px;
    }

    /* --- 按鈕核心 (Touch Friendly) --- */
    .stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        font-family: 'Courier New', monospace !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        padding: 16px 5px !important; /* 增加觸控高度 */
        margin-bottom: 8px !important;
        height: auto !important;
        box-shadow: 0 4px 0 rgba(0,0,0,0.2) !important; /* 實體按壓感 */
        transition: all 0.1s !important;
        color: #ffffff !important;
    }
    .stButton > button:active {
        transform: translateY(4px) !important;
        box-shadow: none !important;
    }

    /* 除法卡 (Secondary) - 橘色 */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(180deg, #f97316 0%, #ea580c 100%) !important;
        border: 1px solid #c2410c !important;
    }

    /* 乘法卡 (Primary) - 紫色 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #a855f7 0%, #7e22ce 100%) !important;
        border: 1px solid #6b21a8 !important;
    }
    
    /* 功能按鈕 (重置/撤銷) - 灰色 */
    .control-btn > button {
        background: #334155 !important;
        border: 1px solid #475569 !important;
        font-size: 0.9rem !important;
        padding: 10px !important;
    }

    /* --- 狀態顯示 --- */
    .status-box {
        padding: 10px; border-radius: 8px; text-align: center;
        font-size: 0.95rem; font-weight: bold; margin-bottom: 10px;
        color: white; animation: fadeIn 0.3s ease;
    }
    .status-neutral { background: rgba(30, 41, 59, 0.9); border: 1px solid #475569; }
    .status-warn { background: rgba(66, 32, 6, 0.9); border: 1px solid #eab308; color: #facc15; }
    .status-success { background: rgba(2, 44, 34, 0.9); border: 1px solid #4ade80; color: #4ade80; }
    .status-error { background: rgba(69, 10, 10, 0.9); border: 1px solid #f87171; color: #fca5a5; }

    /* --- 數學算式 --- */
    .math-display {
        font-size: 1.3rem; font-family: monospace;
        color: #e2e8f0; background: #0f172a;
        padding: 12px; border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin-top: 10px; overflow-x: auto; /* 防止手機溢出 */
        white-space: nowrap;
    }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 領域模型 (Domain Model)
# ==========================================

@dataclass
class OpCard:
    val: int
    op: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_text(self) -> str:
        symbol = "×" if self.op == 'mul' else "÷"
        num_str = f"({self.val})" if self.val < 0 else f"{self.val}"
        return f"{symbol} {num_str}"
    
    @property
    def help_text(self) -> str:
        return "" # 手機版移除 tooltip，改用直觀設計

# ==========================================
# 3. 核心引擎 (Logic Core)
# ==========================================

class VectorEngine:
    @staticmethod
    def generate_level(level: int) -> dict:
        # 難度配置 (保持不變)
        config = {
            1: {'steps': 1, 'ops': ['mul'], 'nums': [2, 3, 4, 5], 'neg_prob': 0.0, 'title': "L1: 引擎啟動"},
            2: {'steps': 1, 'ops': ['mul'], 'nums': [2, 3, 4], 'neg_prob': 1.0, 'title': "L2: 反向推進"},
            3: {'steps': 2, 'ops': ['mul'], 'nums': [2, 3], 'neg_prob': 1.0, 'title': "L3: 雙重翻轉"},
            4: {'steps': 1, 'ops': ['div'], 'nums': [2, 3, 4], 'neg_prob': 0.0, 'title': "L4: 能量壓縮"},
            5: {'steps': 1, 'ops': ['div'], 'nums': [2, 4], 'neg_prob': 1.0, 'title': "L5: 反向壓縮"},
            6: {'steps': 2, 'ops': ['mul', 'div'], 'nums': [2, 3, 4], 'neg_prob': 0.0, 'title': "L6: 混合動力 I"},
            7: {'steps': 2, 'ops': ['mul', 'div'], 'nums': [2, 3], 'neg_prob': 0.6, 'title': "L7: 混合動力 II"},
            8: {'steps': 3, 'ops': ['mul', 'div'], 'nums': [2, 3, 4], 'neg_prob': 0.4, 'title': "L8: 導航策略"},
            9: {'steps': 3, 'ops': ['mul', 'div'], 'nums': [3, 4, 5], 'neg_prob': 0.5, 'title': "L9: 亂流穿越"},
            10: {'steps': 4, 'ops': ['mul', 'div'], 'nums': [2, 3, 5], 'neg_prob': 0.5, 'title': "L10: 超頻極限"}
        }
        cfg = config.get(level, config[10])
        
        start_val = random.choice([1, 2, 3, -1, -2, -3])
        if level == 1: start_val = random.choice([1, 2, 3])
        if level == 3: start_val = random.choice([-1, -2, -3])
        
        current = start_val
        correct_path = []
        
        for _ in range(cfg['steps']):
            op_type = random.choice(cfg['ops'])
            num = random.choice(cfg['nums'])
            if random.random() < cfg['neg_prob']: num = -num
            
            if op_type == 'div':
                if current % num != 0: op_type = 'mul'
            
            if op_type == 'mul': current *= num
            else: current //= num
                
            correct_path.append(OpCard(num, op_type))

        target = current
        
        distractor_count = 2
        if level >= 6: distractor_count = 3
        
        distractors = []
        for _ in range(distractor_count):
            d_op = random.choice(['mul', 'div'])
            d_num = random.choice(cfg['nums'])
            if random.random() < 0.5: d_num = -d_num
            distractors.append(OpCard(d_num, d_op))
            
        hand = correct_path + distractors
        random.shuffle(hand)
        
        return {"start": start_val, "target": target, "hand": hand, "title": cfg['title']}

    @staticmethod
    def calculate_current(start: int, history: List[OpCard]) -> int:
        val = start
        for card in history:
            if card.op == 'mul': val *= card.val
            elif card.op == 'div':
                if card.val == 0: return val
                val = int(val / card.val)
        return val

    @staticmethod
    def generate_vector_html(current: int, target: int) -> str:
        max_limit = max(abs(current), abs(target), 10)
        # 調整比例以適應手機小螢幕
        scale_pct = 40 / max_limit 
        
        def get_bar_style(val, is_target=False):
            w = abs(val) * scale_pct
            # 限制最大寬度防止破版
            if w > 48: w = 48 
            
            if not is_target:
                if val > 0: color_css = "background: linear-gradient(90deg, #3b82f6, #60a5fa);"
                elif val < 0: color_css = "background: linear-gradient(90deg, #ef4444, #f87171);"
                else: return "display:none;"
            else:
                color_css = "background: transparent;"
            
            style = f"position:absolute; top: {'40px' if is_target else '30px'}; height: {'16px' if is_target else '36px'}; width: {w}%;"
            
            if val > 0:
                style += "left: 50%; border-radius: 0 4px 4px 0;"
                if is_target: style += "border: 2px dashed #a6e3a1;"
                else: style += f"{color_css} box-shadow: 0 0 10px rgba(59, 130, 246, 0.4); z-index: 2;"
            else:
                style += f"left: {50 - w}%; border-radius: 4px 0 0 4px;"
                if is_target: style += "border: 2px dashed #fca5a5;"
                else: style += f"{color_css} box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); z-index: 2;"
            return style

        current_bar = get_bar_style(current, False)
        target_bar = get_bar_style(target, True)
        
        # 簡化刻度顯示
        ticks = ""
        ticks += f'<div style="position:absolute; left:50%; top:75px; font-size:10px; color:#64748b; transform:translateX(-50%);">0</div>'
        
        flip_msg = "● 歸零"
        if current < 0: flip_msg = "◀ 反向 (Neg)"
        elif current > 0: flip_msg = "▶ 正向 (Pos)"

        html = f"""
        <div style="width:100%; height:90px; position:relative;">
            <div class="number-line"><div class="center-mark"></div></div>
            <div style="{target_bar}"></div>
            <div style="{current_bar}"></div>
            {ticks}
        </div>
        <div class="flip-indicator">{flip_msg}</div>
        """
        return html

    @staticmethod
    def generate_equation_latex(start: int, history: List[OpCard]) -> str:
        eq_str = f"{start}"
        for card in history:
            symbol = "\\times" if card.op == 'mul' else "\\div"
            val_str = f"({card.val})" if card.val < 0 else f"{card.val}"
            eq_str += f" {symbol} {val_str}"
        return eq_str

# ==========================================
# 4. 狀態管理
# ==========================================

class GameState:
    def __init__(self):
        if 'level' not in st.session_state: self.init_game()
    
    def init_game(self):
        st.session_state.update({
            'level': 1, 'history': [], 'game_status': 'playing',
            'msg': '引擎就緒', 'msg_type': 'neutral'
        })
        self.start_level(1)

    def start_level(self, level):
        st.session_state.level = level
        data = VectorEngine.generate_level(level)
        st.session_state.start_val = data['start']
        st.session_state.target = data['target']
        st.session_state.hand = data['hand']
        st.session_state.level_title = data['title']
        st.session_state.history = []
        st.session_state.game_status = 'playing'
        st.session_state.msg = f"{data['title']}"
        st.session_state.msg_type = 'neutral'

    def play_card(self, card_idx):
        hand = st.session_state.hand
        if 0 <= card_idx < len(hand):
            card = hand.pop(card_idx)
            st.session_state.history.append(card)
            self._check_status()

    def undo(self):
        if st.session_state.history:
            card = st.session_state.history.pop()
            st.session_state.hand.append(card)
            st.session_state.game_status = 'playing'
            st.session_state.msg = "撤銷操作"

    def retry(self):
        self.start_level(st.session_state.level)

    def _check_status(self):
        current = VectorEngine.calculate_current(st.session_state.start_val, st.session_state.history)
        target = st.session_state.target
        
        if current == target:
            st.session_state.game_status = 'won'
            st.session_state.msg = "✨ 同步成功！"
            st.session_state.msg_type = 'success'
        elif not st.session_state.hand:
            st.session_state.game_status = 'lost'
            st.session_state.msg = "💀 動力耗盡"
            st.session_state.msg_type = 'error'
        else:
            if (current > 0 and target < 0) or (current < 0 and target > 0):
                st.session_state.msg = "⚠️ 方向錯誤！需負數卡"
                st.session_state.msg_type = 'warn'
            elif abs(current) < abs(target):
                st.session_state.msg = "📉 強度不足 (需 ×)"
                st.session_state.msg_type = 'neutral'
            elif abs(current) > abs(target):
                st.session_state.msg = "📈 強度過載 (需 ÷)"
                st.session_state.msg_type = 'warn'
            else:
                st.session_state.msg = "計算中..."

    def next_level(self):
        if st.session_state.level >= MAX_LEVEL:
            st.session_state.game_status = 'completed'
        else: self.start_level(st.session_state.level + 1)
    
    def restart_game(self): self.init_game()

# ==========================================
# 5. UI 呈現 (Mobile Layout)
# ==========================================

def main():
    game = GameState()
    
    # Header: 緊湊佈局
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.markdown(f"<h3 style='margin:0; padding:0;'>🚀 Lv.{st.session_state.level}</h3>", unsafe_allow_html=True)
        st.caption(st.session_state.level_title)
    with c2:
        # 使用自定義 CSS class 的按鈕
        st.markdown('<div class="control-btn">', unsafe_allow_html=True)
        if st.button("🔄", help="重置"): game.restart_game(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    progress = st.session_state.level / MAX_LEVEL
    st.progress(progress)

    if st.session_state.game_status == 'completed':
        st.balloons()
        st.success("🏆 向量大師！")
        if st.button("🎓 再玩一次", use_container_width=True): game.restart_game(); st.rerun()
        return

    # Dashboard: 手機版使用 3 列但更緊湊
    target = st.session_state.target
    current = VectorEngine.calculate_current(st.session_state.start_val, st.session_state.history)
    
    # 使用 container 包裹以控制背景
    with st.container():
        col_start, col_mid, col_tgt = st.columns([1, 0.5, 1])
        with col_start:
            st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:0.8rem;'>當前</div>", unsafe_allow_html=True)
            c_color = "#3b82f6" if current > 0 else "#ef4444"
            if current == 0: c_color = "#ffffff"
            st.markdown(f"<div style='text-align:center; font-size:1.8rem; font-weight:900; color:{c_color};'>{current}</div>", unsafe_allow_html=True)
            
        with col_mid:
            icon = "⏩"
            if st.session_state.game_status == 'won': icon = "✅"
            elif st.session_state.game_status == 'lost': icon = "❌"
            st.markdown(f"<div style='text-align:center; font-size:1.5rem; padding-top:10px;'>{icon}</div>", unsafe_allow_html=True)
            
        with col_tgt:
            st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:0.8rem;'>目標</div>", unsafe_allow_html=True)
            t_color = "#3b82f6" if target > 0 else "#ef4444"
            if target == 0: t_color = "#ffffff"
            st.markdown(f"<div style='text-align:center; font-size:1.8rem; font-weight:900; color:{t_color}; border:2px dashed {t_color}; border-radius:8px;'>{target}</div>", unsafe_allow_html=True)

    # Status Message
    msg_cls = f"status-{st.session_state.msg_type}"
    st.markdown(f'<div class="status-box {msg_cls}">{st.session_state.msg}</div>', unsafe_allow_html=True)

    # Visualizer
    vector_html = VectorEngine.generate_vector_html(current, target)
    st.markdown(f'<div class="vector-scope">{vector_html}</div>', unsafe_allow_html=True)
    
    # Equation
    latex_eq = VectorEngine.generate_equation_latex(st.session_state.start_val, st.session_state.history)
    st.markdown(f'<div class="math-display">$${latex_eq} = {current}$$</div>', unsafe_allow_html=True)

    # Controls Area
    st.markdown("---")
    if st.session_state.game_status == 'playing':
        hand = st.session_state.hand
        if hand:
            # 手機版：每行 2 張卡片，更易點擊
            cols = st.columns(2)
            for i, card in enumerate(hand):
                with cols[i % 2]:
                    btn_type = "primary" if card.op == 'mul' else "secondary"
                    if st.button(card.display_text, key=f"card_{card.id}", type=btn_type, use_container_width=True):
                        game.play_card(i)
                        st.rerun()
        
        if st.session_state.history:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            if st.button("↩️ 撤銷", use_container_width=True): game.undo(); st.rerun()

    elif st.session_state.game_status == 'won':
        if st.button("🚀 下一關", type="primary", use_container_width=True): game.next_level(); st.rerun()
    elif st.session_state.game_status == 'lost':
        if st.button("💥 重試", type="primary", use_container_width=True): game.retry(); st.rerun()

if __name__ == "__main__":
    main()
