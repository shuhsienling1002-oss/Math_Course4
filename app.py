import streamlit as st
import random
import uuid
import math
from dataclasses import dataclass, field
from typing import List, Dict

# ==========================================
# 0. 全局設定
# ==========================================
MAX_LEVEL = 10

# ==========================================
# 1. 核心配置與 CSS (High Contrast Vector Style)
# ==========================================
st.set_page_config(
    page_title="整數極限：向量超頻 v1.0",
    page_icon="🚀",
    layout="centered"
)

st.markdown("""
<style>
    /* 全局設定 */
    .stApp { background-color: #020617; color: #f8fafc; }
    .stProgress > div > div > div > div { background-color: #a855f7; } /* 紫色進度條 */
    .stCaption { color: #94a3b8 !important; }

    /* 向量儀表板容器 */
    .vector-scope {
        background: #0f172a;
        border: 2px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.2);
        position: relative;
        overflow: hidden;
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }

    /* 數線背景 */
    .number-line {
        width: 100%;
        height: 4px;
        background: #475569;
        position: relative;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .center-mark {
        position: absolute;
        left: 50%; top: -10px;
        width: 2px; height: 24px;
        background: #ffffff;
        z-index: 5;
    }

    /* 向量箭頭 */
    .vector-arrow {
        height: 12px;
        position: absolute;
        top: -4px;
        left: 50%; /* 起點永遠在 0 */
        transform-origin: left center;
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* 彈性動畫 */
        display: flex;
        align-items: center;
        border-radius: 4px;
    }
    
    /* 正向向量 (藍) */
    .vec-pos {
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
        box-shadow: 0 0 10px #3b82f6;
    }
    
    /* 負向向量 (紅) - CSS transform 會處理方向 */
    .vec-neg {
        background: linear-gradient(90deg, #ef4444, #f87171);
        box-shadow: 0 0 10px #ef4444;
    }

    /* 翻轉動畫提示 */
    .flip-indicator {
        font-size: 0.8rem;
        color: #facc15;
        font-weight: bold;
        margin-top: 5px;
        text-shadow: 0 0 5px #facc15;
    }

    /* 操作卡牌按鈕 */
    div.stButton > button {
        border-radius: 8px !important;
        font-family: 'Courier New', monospace !important;
        font-size: 1.2rem !important;
        font-weight: 900 !important;
        border: 2px solid rgba(255,255,255,0.1) !important;
        color: #ffffff !important;
        padding: 15px 10px !important;
        height: auto !important;
    }

    /* 乘法卡 (紫) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(145deg, #7e22ce, #6b21a8) !important;
        border-color: #a855f7 !important;
    }
    div.stButton > button[kind="primary"]:hover { background: #9333ea !important; transform: scale(1.05); }

    /* 除法卡 (橘) */
    div.stButton > button[kind="secondary"] {
        background: linear-gradient(145deg, #c2410c, #9a3412) !important;
        border-color: #f97316 !important;
    }
    div.stButton > button[kind="secondary"]:hover { background: #ea580c !important; transform: scale(1.05); }

    /* 狀態框 */
    .status-box {
        padding: 12px; border-radius: 8px; text-align: center;
        font-weight: bold; margin-bottom: 10px; color: white;
        text-shadow: 0 1px 2px black;
    }
    .status-neutral { background: #1e293b; border: 1px solid #94a3b8; }
    .status-warn { background: #422006; border: 1px solid #eab308; color: #facc15; }
    .status-success { background: #052e16; border: 1px solid #4ade80; color: #4ade80; }
    .status-error { background: #450a0a; border: 1px solid #f87171; color: #fca5a5; }

    /* 數學顯示 */
    .math-display {
        font-size: 1.6rem; font-family: monospace;
        color: #ffffff; background: #000000;
        padding: 15px; border-radius: 8px;
        border: 1px solid #334155; border-left: 6px solid #f59e0b; /* 橘色邊條 */
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 領域模型 (Domain Model)
# ==========================================

@dataclass
class OpCard:
    val: int  # 運算數值，如 2, -3
    op: str   # 'mul' or 'div'
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_text(self) -> str:
        # 視覺化符號
        symbol = "×" if self.op == 'mul' else "÷"
        # 負數加括號
        num_str = f"({self.val})" if self.val < 0 else f"{self.val}"
        return f"{symbol} {num_str}"
    
    @property
    def help_text(self) -> str:
        action = "放大" if self.op == 'mul' and abs(self.val) > 1 else "縮小"
        if self.op == 'mul' and self.val == 1: action = "維持"
        
        flip = "並翻轉方向" if self.val < 0 else "方向不變"
        return f"{action} {abs(self.val)} 倍，{flip}"

# ==========================================
# 3. 核心引擎 (Logic Layer)
# ==========================================

class VectorEngine:
    @staticmethod
    def generate_level(level: int) -> dict:
        """
        10關乘除法進階設計：
        1. 正整數乘法 (放大)
        2. 負整數乘法 (翻轉+放大)
        3. 負負得正 (雙重翻轉)
        4. 基礎除法 (縮小)
        5. 負數除法 (翻轉+縮小)
        6. 乘除混合 (正數)
        7. 乘除混合 (含負數)
        8. 策略路徑 (需先除後乘避免溢出)
        9. 大數運算 (高階心算)
        10. 終極向量 (長鏈運算)
        """
        config = {
            1: {'steps': 1, 'ops': ['mul'], 'nums': [2, 3, 4, 5], 'neg_prob': 0.0, 'title': "L1: 向量引擎啟動 (正數乘法)"},
            2: {'steps': 1, 'ops': ['mul'], 'nums': [2, 3, 4], 'neg_prob': 1.0, 'title': "L2: 反向推進器 (負數乘法)"},
            3: {'steps': 2, 'ops': ['mul'], 'nums': [2, 3], 'neg_prob': 1.0, 'title': "L3: 雙重翻轉 (負負得正)"},
            4: {'steps': 1, 'ops': ['div'], 'nums': [2, 3, 4], 'neg_prob': 0.0, 'title': "L4: 能量壓縮 (正數除法)"},
            5: {'steps': 1, 'ops': ['div'], 'nums': [2, 4], 'neg_prob': 1.0, 'title': "L5: 反向壓縮 (負數除法)"},
            6: {'steps': 2, 'ops': ['mul', 'div'], 'nums': [2, 3, 4], 'neg_prob': 0.0, 'title': "L6: 混合動力 I (正數混合)"},
            7: {'steps': 2, 'ops': ['mul', 'div'], 'nums': [2, 3], 'neg_prob': 0.6, 'title': "L7: 混合動力 II (全混合)"},
            8: {'steps': 3, 'ops': ['mul', 'div'], 'nums': [2, 3, 4], 'neg_prob': 0.4, 'title': "L8: 導航策略 (運算順序)"},
            9: {'steps': 3, 'ops': ['mul', 'div'], 'nums': [3, 4, 5], 'neg_prob': 0.5, 'title': "L9: 亂流穿越 (大數挑戰)"},
            10: {'steps': 4, 'ops': ['mul', 'div'], 'nums': [2, 3, 5], 'neg_prob': 0.5, 'title': "L10: 超頻極限 (最終試煉)"}
        }
        cfg = config.get(level, config[10])
        
        # 1. 隨機生成起始值 (Start)
        # 為了避免除法出現分數，我們先生成路徑，反推 Start 和 Target
        # 但為了簡單，我們設定一個合理的 Start，然後確保每一步乘除都合法
        
        start_val = random.choice([1, 2, 3, -1, -2, -3])
        if level == 1: start_val = random.choice([1, 2, 3]) # L1 簡單點
        if level == 3: start_val = random.choice([-1, -2, -3]) # L3 從負開始
        
        current = start_val
        correct_path = []
        
        for _ in range(cfg['steps']):
            op_type = random.choice(cfg['ops'])
            num = random.choice(cfg['nums'])
            
            # 決定正負
            if random.random() < cfg['neg_prob']:
                num = -num
            
            # 如果是除法，必須保證整除
            if op_type == 'div':
                # 如果不能整除，強制改為乘法，或者調整 num
                if current % num != 0:
                    # 策略：改為乘法，或者讓 num 變成 current 的因數
                    # 簡單起見，直接改乘法，除非 current 很大
                    op_type = 'mul'
            
            # 執行運算
            if op_type == 'mul':
                current *= num
            else:
                current //= num
                
            correct_path.append(OpCard(num, op_type))

        target = current
        
        # 2. 生成干擾項
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
            if card.op == 'mul':
                val *= card.val
            elif card.op == 'div':
                # 注意：Python 的 // 對負數除法行為可能與數學直覺不同 (向下取整)
                # 例如 -3 // 2 = -2。但我們這裡設計為整除，所以用 int(val / card.val) 更安全
                if card.val == 0: return val # 防呆
                val = int(val / card.val)
        return val

    @staticmethod
    def generate_vector_html(current: int, target: int) -> str:
        """
        [Visual Engine] 向量視覺化
        使用 CSS 寬度和顏色來模擬數線上的向量
        """
        # 定義最大顯示範圍 (Scale)，避免超出邊界
        # 取 max(|current|, |target|, 20)
        max_limit = max(abs(current), abs(target), 10)
        scale_factor = 90 / (max_limit * 2) # 90% 寬度 / 總範圍
        
        # 計算 Current 的寬度與方向
        curr_width = abs(current) * scale_factor * 2 # *2 因為 scale_factor 是基於總長
        # 修正： scale_factor 應該是 50% (半長) / max_limit
        scale_pct = 45 / max_limit # 留 5% 邊距
        
        c_width_pct = abs(current) * scale_pct
        t_width_pct = abs(target) * scale_pct
        
        # 方向 (左/右)
        # CSS 中，我們以中心 (50%) 為基準
        # 正數： left: 50%, width: x
        # 負數： right: 50%, width: x (或者 left: 50-x, width: x)
        
        def get_bar_style(val, is_target=False):
            w = abs(val) * scale_pct
            color = "#a855f7" if not is_target else "rgba(255, 255, 255, 0.3)" # Target 是幽靈
            if not is_target:
                if val > 0: color = "linear-gradient(90deg, #3b82f6, #60a5fa)" # Blue
                elif val < 0: color = "linear-gradient(90deg, #f87171, #ef4444)" # Red (gradient flipped visually)
                else: return "display:none;" # 0
            
            style = f"position:absolute; top: {'40px' if is_target else '30px'}; height: {'16px' if is_target else '36px'}; width: {w}%;"
            
            if val > 0:
                style += "left: 50%; border-radius: 0 4px 4px 0;"
                if is_target: style += "border: 2px dashed #a6e3a1; background: transparent;"
            else:
                style += f"left: {50 - w}%; border-radius: 4px 0 0 4px;"
                if is_target: style += "border: 2px dashed #fca5a5; background: transparent;"
                
            if not is_target:
                style += "box-shadow: 0 0 15px rgba(255,255,255,0.4); z-index: 2;"
            else:
                style += "z-index: 1;"
                
            return style

        current_bar = get_bar_style(current, False)
        target_bar = get_bar_style(target, True)
        
        # 刻度線
        ticks = ""
        # 簡單畫幾個刻度： -Limit, 0, +Limit
        ticks += f'<div style="position:absolute; left:50%; top:70px; font-size:12px; color:#94a3b8; transform:translateX(-50%);">0</div>'
        ticks += f'<div style="position:absolute; left:5%; top:70px; font-size:12px; color:#94a3b8;">-{max_limit}</div>'
        ticks += f'<div style="position:absolute; right:5%; top:70px; font-size:12px; color:#94a3b8;">+{max_limit}</div>'

        # 狀態文字
        flip_msg = ""
        if current < 0: flip_msg = "◀ 反向 (Negative)"
        elif current > 0: flip_msg = "▶ 正向 (Positive)"
        else: flip_msg = "● 歸零 (Zero)"

        html = f"""
        <div style="width:100%; height:100px; position:relative;">
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
            'msg': '向量引擎就緒。請調整倍率至目標強度。', 'msg_type': 'neutral'
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
        st.session_state.msg = f"🚀 {data['title']}"
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
            st.session_state.msg = "↺ 撤銷操作"

    def retry(self):
        self.start_level(st.session_state.level)

    def _check_status(self):
        current = VectorEngine.calculate_current(st.session_state.start_val, st.session_state.history)
        target = st.session_state.target
        
        # 檢查是否整除 (防止分數出現)
        is_integer = True
        # 實際上 calculate_current 已經做了 int 轉換，但我們可以檢查中間過程
        # 這裡簡化：只要結果對了就對
        
        if current == target:
            st.session_state.game_status = 'won'
            st.session_state.msg = "✨ 頻率同步！目標鎖定！"
            st.session_state.msg_type = 'success'
        elif not st.session_state.hand:
            st.session_state.game_status = 'lost'
            st.session_state.msg = "💀 動力耗盡，同步失敗。"
            st.session_state.msg_type = 'error'
        else:
            # 向量方向提示
            if (current > 0 and target < 0) or (current < 0 and target > 0):
                st.session_state.msg = "⚠️ 方向錯誤！需要負數卡來翻轉 (Flip)！"
                st.session_state.msg_type = 'warn'
            elif abs(current) < abs(target):
                st.session_state.msg = "📉 強度不足，需要放大 (×)。"
                st.session_state.msg_type = 'neutral'
            elif abs(current) > abs(target):
                st.session_state.msg = "📈 強度過載，需要縮小 (÷)。"
                st.session_state.msg_type = 'warn'
            else:
                st.session_state.msg = "計算中..."

    def next_level(self):
        if st.session_state.level >= MAX_LEVEL:
            st.session_state.game_status = 'completed'
        else: self.start_level(st.session_state.level + 1)
    
    def restart_game(self): self.init_game()

# ==========================================
# 5. UI 呈現
# ==========================================

def main():
    game = GameState()
    
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🚀 整數極限：向量超頻")
    with c2:
        if st.button("🔄 重置"): game.restart_game(); st.rerun()

    progress = st.session_state.level / MAX_LEVEL
    st.progress(progress)
    st.caption(f"Lv {st.session_state.level} / {MAX_LEVEL}")

    if st.session_state.game_status == 'completed':
        st.balloons()
        st.success("🏆 向量大師！你已掌握時空變換的奧義！")
        if st.button("🎓 再玩一次", use_container_width=True): game.restart_game(); st.rerun()
        return

    # Dashboard
    target = st.session_state.target
    current = VectorEngine.calculate_current(st.session_state.start_val, st.session_state.history)
    
    col_start, col_mid, col_tgt = st.columns([1, 0.2, 1])
    with col_start:
        st.markdown(f"<div style='text-align:center; color:#94a3b8; font-weight:bold;'>當前強度</div>", unsafe_allow_html=True)
        c_color = "#3b82f6" if current > 0 else "#ef4444"
        if current == 0: c_color = "#ffffff"
        st.markdown(f"<div style='text-align:center; font-size:2.2rem; font-weight:900; color:{c_color};'>{current}</div>", unsafe_allow_html=True)
        
    with col_mid:
        icon = "⏩"
        if st.session_state.game_status == 'won': icon = "✅"
        elif st.session_state.game_status == 'lost': icon = "❌"
        st.markdown(f"<div style='text-align:center; font-size:2rem; padding-top:20px;'>{icon}</div>", unsafe_allow_html=True)
        
    with col_tgt:
        st.markdown(f"<div style='text-align:center; color:#94a3b8; font-weight:bold;'>目標強度</div>", unsafe_allow_html=True)
        t_color = "#3b82f6" if target > 0 else "#ef4444"
        if target == 0: t_color = "#ffffff"
        st.markdown(f"<div style='text-align:center; font-size:2.2rem; font-weight:900; color:{t_color}; border:2px dashed {t_color}; border-radius:8px;'>{target}</div>", unsafe_allow_html=True)

    # Status
    msg_cls = f"status-{st.session_state.msg_type}"
    st.markdown(f'<div class="status-box {msg_cls}">{st.session_state.msg}</div>', unsafe_allow_html=True)

    # Vector Visualizer
    st.markdown("**⚛️ 向量示波器 (Vector Scope)：**")
    vector_html = VectorEngine.generate_vector_html(current, target)
    st.markdown(f'<div class="vector-scope">{vector_html}</div>', unsafe_allow_html=True)
    
    # Equation
    latex_eq = VectorEngine.generate_equation_latex(st.session_state.start_val, st.session_state.history)
    st.markdown(f'<div class="math-display">{latex_eq} = {current}</div>', unsafe_allow_html=True)

    # Controls
    if st.session_state.game_status == 'playing':
        st.write("👇 選擇運算模組：")
        hand = st.session_state.hand
        if hand:
            cols = st.columns(4)
            for i, card in enumerate(hand):
                with cols[i % 4]:
                    # Primary for Mul, Secondary for Div
                    btn_kind = "primary" if card.op == 'mul' else "secondary"
                    if st.button(card.display_text, key=f"card_{card.id}", type="primary" if btn_kind=="primary" else "secondary", help=card.help_text, use_container_width=True):
                        # Streamlit doesn't support custom attributes easily, rely on CSS selection or just standard types
                        # The CSS selector div.stButton > button[kind="primary"] won't work directly because Streamlit doesn't pass 'kind'.
                        # We rely on the button text or standard Streamlit types.
                        # Workaround: Streamlit's 'type' arg maps to classes. 
                        # type="primary" -> Red/White in standard, but we overrode it.
                        # type="secondary" -> default.
                        game.play_card(i)
                        st.rerun()
            
            # 由於 Streamlit 按鈕樣式限制，CSS 中針對 primary/secondary 的選擇器可能無法完美生效
            # 這裡補充說明：紫色是乘法，橘色是除法 (若 CSS 注入成功)
        
        if st.session_state.history:
            st.markdown("---")
            if st.button("↩️ 撤銷 (Undo)"): game.undo(); st.rerun()

    elif st.session_state.game_status == 'won':
        if st.button("🚀 下一關", type="primary", use_container_width=True): game.next_level(); st.rerun()
    elif st.session_state.game_status == 'lost':
        if st.button("💥 重試", type="primary", use_container_width=True): game.retry(); st.rerun()

if __name__ == "__main__":
    main()
