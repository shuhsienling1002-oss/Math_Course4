import streamlit as st
import random
import math
from fractions import Fraction
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ==========================================
# 1. 配置與 CSS (View Layer - UI/UX-CRF)
# ==========================================
st.set_page_config(page_title="分數拼湊大作戰 v2.0", page_icon="🧩", layout="centered")

# 使用 提到的視覺層級與色彩心理學
st.markdown("""
<style>
    .stApp { background-color: #1e1e2e; color: #cdd6f4; }
    
    /* 遊戲容器 */
    .game-container {
        background: #313244;
        border-radius: 16px;
        padding: 24px;
        border: 2px solid #45475a;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    /* 分數視覺化 (圓餅圖) - 第一性原理 */
    .pie-chart {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: conic-gradient(#89b4fa var(--p), #45475a 0);
        display: inline-block;
        vertical-align: middle;
        margin-right: 8px;
        border: 2px solid #cba6f7;
    }
    .pie-chart.negative {
        background: conic-gradient(#f38ba8 var(--p), #45475a 0);
        border-color: #f38ba8;
    }

    /* 卡片樣式優化 */
    div.stButton > button {
        background-color: #cba6f7 !important;
        color: #181825 !important;
        border-radius: 12px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        height: auto !important;
        padding: 10px 5px !important;
        border: 2px solid transparent !important;
    }
    div.stButton > button:hover {
        border-color: #f5c2e7 !important;
        transform: translateY(-2px);
    }
    
    /* 進度條與標記 */
    .progress-track {
        background: #45475a;
        height: 30px;
        border-radius: 15px;
        position: relative;
        overflow: hidden;
        margin: 20px 0;
        box-shadow: inset 0 2px 5px rgba(0,0,0,0.2);
    }
    .progress-fill {
        height: 100%;
        transition: width 0.5s ease-out;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 10px;
        font-size: 12px;
        font-weight: bold;
        color: #181825;
    }
    .fill-normal { background: linear-gradient(90deg, #89b4fa, #74c7ec); }
    .fill-warning { background: linear-gradient(90deg, #f9e2af, #fab387); } /* 基礎比率預警 */
    .fill-danger { background: linear-gradient(90deg, #f38ba8, #eba0ac); }
    
    .target-line {
        position: absolute;
        top: 0; bottom: 0;
        width: 4px;
        background: #a6e3a1;
        z-index: 10;
        box-shadow: 0 0 10px #a6e3a1;
    }

    /* 數學推導區 */
    .math-log {
        font-family: 'Courier New', monospace;
        background: #181825;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #f9e2af;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 數據模型 (Data Model)
# ==========================================

@dataclass
class Card:
    numerator: int
    denominator: int
    id: int = field(default_factory=lambda: random.randint(10000, 99999))

    @property
    def value(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    @property
    def is_negative(self) -> bool:
        return self.numerator < 0

    def get_visual_html(self) -> str:
        """生成符合第一性原理的視覺化 HTML"""
        # 計算圓餅圖百分比 (絕對值)
        percent = abs(self.numerator / self.denominator) * 100
        # 限制在 100% 以內避免圖形崩壞 (超過1的用滿圓表示)
        percent_css = min(percent, 100)
        
        css_class = "pie-chart negative" if self.is_negative else "pie-chart"
        sign_str = "-" if self.is_negative else "+"
        # 使用 CSS 變量傳遞百分比
        return f"""
        <div style="display:flex; align-items:center; justify-content:center;">
            <div class="{css_class}" style="--p: {percent_css}%;"></div>
            <span>{self.numerator}/{self.denominator}</span>
        </div>
        """

# ==========================================
# 3. 核心引擎 (Logic Layer - Code-CRF)
# ==========================================

class GameEngine:
    def __init__(self):
        # 路徑依賴 - 初始化狀態確保路徑正確
        if 'game_state' not in st.session_state:
            self.reset_game()

    def reset_game(self):
        st.session_state.level = 1
        st.session_state.score = 0
        self.start_level(1)

    def start_level(self, level: int):
        st.session_state.level = level
        
        # 擁抱混亂 - 增加重試熔斷機制
        retry_count = 0
        while retry_count < 10:
            target, start_val, hand, correct_subset, title = self._generate_math_data(level)
            if target > 0: # 確保目標合理
                break
            retry_count += 1
        
        st.session_state.target = target
        st.session_state.current = start_val
        st.session_state.hand = hand # 牌庫
        st.session_state.played_cards = [] # 逆向思維 - 記錄出牌歷史以支持悔棋
        st.session_state.correct_hand_cache = correct_subset
        st.session_state.level_title = title
        st.session_state.game_state = 'playing'
        st.session_state.msg = f"Level {level}: {title}"
        st.session_state.feedback_header = "" 
        st.session_state.math_log = ""

    def _generate_math_data(self, level: int) -> Tuple[Fraction, Fraction, List[Card], List[Card], str]:
        """
        難度曲線設計 - 符合認知負荷
        """
        target_val = Fraction(0, 1)
        correct_hand = []
        allow_negative = False
        level_title = ""
        
        # Lv 1-3: 物理錨定 (同分母 -> 簡單異分母)
        if level == 1:
            den_pool, steps, level_title = [2], 2, "暖身：二分之一的世界"
        elif level == 2:
            den_pool, steps, level_title = [2, 4], 2, "進階：切蛋糕 (2與4)"
        elif level == 3:
            den_pool, steps, level_title = [2, 3, 4, 6], 3, "挑戰：尋找公倍數"
        # Lv 4+: 負數覺醒 (引入反向向量)
        elif level == 4:
            den_pool, steps, allow_negative, level_title = [2, 4], 3, True, "逆向：引入負數 (紅色)"
        elif level == 5:
            den_pool, steps, allow_negative, level_title = [2, 5, 10], 3, True, "混合：十進位的直覺"
        else:
            den_pool, steps, allow_negative, level_title = [3, 4, 5, 6, 8], 4, True, "大師：極限運算"

        # 生成正確路徑 (Nash Equilibrium - 確保有解)
        for _ in range(steps):
            d = random.choice(den_pool)
            n = random.choice([1, 1, 2])
            if allow_negative and random.random() < (0.5 if level >= 4 else 0):
                n = -n
            card = Card(n, d)
            correct_hand.append(card)
            target_val += card.value

        # 混入干擾項 (Entropy)
        distractors = [Card(random.choice([1, 2]) * (-1 if allow_negative and random.random()<0.4 else 1), random.choice(den_pool)) for _ in range(2)]
        final_hand = correct_hand + distractors
        random.shuffle(final_hand)
        
        return target_val, Fraction(0, 1), final_hand, correct_hand, level_title

    def play_card(self, card_idx: int):
        """高內聚的動作處理"""
        if st.session_state.game_state != 'playing': return
        
        hand = st.session_state.hand
        if 0 <= card_idx < len(hand):
            card = hand.pop(card_idx) # 從手牌移除
            st.session_state.current += card.value
            st.session_state.played_cards.append(card) # 加入歷史紀錄 (支持 Undo)
            self._check_win_condition()

    def undo_last_move(self):
        """反脆弱 - 允許悔棋，降低錯誤成本"""
        if st.session_state.played_cards and st.session_state.game_state == 'playing':
            card = st.session_state.played_cards.pop()
            st.session_state.current -= card.value
            st.session_state.hand.append(card)
            st.session_state.msg = "↩️ 已撤銷上一步"

    def _check_win_condition(self):
        curr = st.session_state.current
        tgt = st.session_state.target
        hand = st.session_state.hand
        
        # 臨界質量 - 判斷勝負
        if curr == tgt:
            self._trigger_end_game('won')
        elif curr > tgt:
            has_negative = any(c.numerator < 0 for c in hand)
            if not has_negative:
                self._trigger_end_game('lost_over')
            else:
                diff = curr - tgt
                st.session_state.msg = f"⚠️ 超過 {diff}！快用紅色負數牌修正！"
        elif not hand:
            self._trigger_end_game('lost_empty')
        else:
            st.session_state.msg = "計算中..."

    def _trigger_end_game(self, status):
        st.session_state.game_state = status
        if status == 'won':
            st.session_state.msg = "🎉 挑戰成功！"
            st.session_state.feedback_header = "✅ 完美平衡！"
        elif status == 'lost_over':
            st.session_state.msg = "💥 爆掉了！"
            st.session_state.feedback_header = "❌ 超過目標且無法回頭。"
        elif status == 'lost_empty':
            st.session_state.msg = "💀 牌用光了！"
            st.session_state.feedback_header = "❌ 資源耗盡。"
            
        # 生成解析日誌
        self._generate_math_log()

    def _generate_math_log(self):
        # 這裡簡化生成邏輯，專注於顯示正確組合
        cards = st.session_state.correct_hand_cache
        total = sum(c.value for c in cards)
        steps_html = "<ul>"
        for c in cards:
            sign = "-" if c.is_negative else "+"
            steps_html += f"<li>{c.numerator}/{c.denominator} ({sign})</li>"
        steps_html += f"<li><b>總和: {total}</b></li></ul>"
        
        st.session_state.math_log = f"""
        <div class="math-log">
            <b>💡 最佳解法 (Nash Equilibrium):</b><br>
            目標: {st.session_state.target}<br>
            組合: {steps_html}
        </div>
        """

    def next_level(self):
        self.start_level(st.session_state.level + 1)

    def retry_level(self):
        self.start_level(st.session_state.level)

# ==========================================
# 4. UI 渲染層 (View Renderer)
# ==========================================

def render_progress_bar(current: Fraction, target: Fraction):
    # 視覺化 - 向量進度條
    if target == 0: target = Fraction(1,1)
    max_val = max(target * Fraction(3, 2), Fraction(2, 1)) # 動態最大值
    
    curr_pct = float(current / max_val) * 100
    tgt_pct = float(target / max_val) * 100
    
    fill_class = "fill-normal"
    if current > target: fill_class = "fill-warning" # 基礎比率警告
    
    st.markdown(f"""
    <div class="game-container">
        <div style="display: flex; justify-content: space-between; font-family: monospace; margin-bottom:5px;">
            <span>🏁 0</span>
            <span style="color: #a6e3a1; font-weight:bold;">目標: {target}</span>
        </div>
        <div class="progress-track">
            <div class="target-line" style="left: {tgt_pct}%;"></div>
            <div class="progress-fill {fill_class}" style="width: {max(0, min(curr_pct, 100))}%;">
                {current}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 5. 主程式 (Main Loop)
# ==========================================

engine = GameEngine()

st.title(f"🧩 分數拼湊大作戰")
st.caption(f"Level {st.session_state.get('level', 1)}: {st.session_state.get('level_title', '')}")

# 狀態訊息區
st.info(st.session_state.get('msg', '歡迎回來'))

# 渲染進度條
render_progress_bar(st.session_state.get('current', Fraction(0,1)), st.session_state.get('target', Fraction(1,1)))

# 遊戲互動區
if st.session_state.game_state == 'playing':
    st.write("### 🎴 出牌 (點擊卡片)")
    
    hand = st.session_state.get('hand', [])
    if hand:
        cols = st.columns(4) # 限制每行 4 張，避免過擠
        for i, card in enumerate(hand):
            with cols[i % 4]:
                # 第一性原理 - 按鈕內包含視覺化 HTML
                # 注意：Streamlit 按鈕不支援複雜 HTML，這裡我們用圖像化的文字替代，或使用 st.markdown 模擬
                # 為了穩定性，這裡使用優化過的文字標籤，但在 CSS 中我們增強了樣式
                if st.button(f"{card.numerator}/{card.denominator}", key=f"card_{card.id}", use_container_width=True):
                    engine.play_card(i)
                    st.rerun()
                # 在按鈕下方顯示圓餅圖 (Visual Aid)
                st.markdown(card.get_visual_html(), unsafe_allow_html=True)
    else:
        st.warning("手牌已空")
    
    st.divider()
    # 反脆弱 - 悔棋按鈕
    if st.session_state.get('played_cards'):
        if st.button("↩️ 悔棋 (Undo)", help="撤銷上一步操作"):
            engine.undo_last_move()
            st.rerun()

else:
    # 結算畫面
    st.markdown("---")
    if st.session_state.game_state == 'won':
        st.success(st.session_state.feedback_header)
        st.balloons()
    else:
        st.error(st.session_state.feedback_header)
    
    st.markdown(st.session_state.math_log, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 重試本關 (Retry)", use_container_width=True):
            engine.retry_level()
            st.rerun()
    with c2:
        if st.session_state.game_state == 'won':
            if st.button("🚀 下一關 (Next Level)", type="primary", use_container_width=True):
                engine.next_level()
                st.rerun()

# 側邊欄：教育指引
with st.sidebar:
    st.markdown("### 📘 戰術指南")
    st.markdown("""
    * **圓餅圖** 代表分數的大小 (第一性原理)。
    * **紅色** 代表負數，會讓進度條倒退。
    * **目標線 (綠色)** 是你必須精準停靠的地方。
    * 若不小心算錯，隨時可以使用 **悔棋**。
    """)
    st.progress(min(st.session_state.level / 10, 1.0))
