# app.py (診断用：肘トルクの3軸成分をプロット)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import japanize_matplotlib
import io
import re
import os

st.set_page_config(layout="wide")
st.title('🔬 肘関節トルク 軸診断ツール')
st.info('まず、肘の外反トルクがX, Y, Zのどの軸に記録されているかを確認します。')

# --- Sidebar for User Inputs ---
with st.sidebar:
    st.header('ステップ1: 解析設定')
    side_to_analyze = st.radio(
        '投手の利き腕を選択してください',
        ('R', 'L'),
        format_func=lambda x: '右投手' if x == 'R' else '左投手'
    )

    st.header('ステップ2: ファイルをアップロード')
    uploaded_file = st.file_uploader(
        f"診断したい{side_to_analyze}投手のExcelファイルを1つだけアップロードしてください",
        type=['xlsx']
    )

# --- Main Panel for Analysis and Results ---
if uploaded_file:
    st.header('3軸トルクのプロット結果')
    
    with st.spinner('データを処理中...'):
        try:
            df = pd.read_excel(uploaded_file, header=[0, 1, 2])
            
            # Create a time axis (in seconds, not normalized)
            time = np.arange(len(df)) / 200

            # --- Extract Moment data for all 3 axes of the elbow joint ---
            moment_x = df[(f'{side_to_analyze}ElbowMoment', 'X', 'N.mm/kg')]
            moment_y = df[(f'{side_to_analyze}ElbowMoment', 'Y', 'N.mm/kg')]
            moment_z = df[(f'{side_to_analyze}ElbowMoment', 'Z', 'N.mm/kg')]

            # --- Plotting ---
            fig, ax = plt.subplots(figsize=(12, 7))

            ax.plot(time, moment_x, label='肘関節 X軸 トルク', color='red', linewidth=2)
            ax.plot(time, moment_y, label='肘関節 Y軸 トルク', color='green', linewidth=2)
            ax.plot(time, moment_z, label='肘関節 Z軸 トルク', color='blue', linewidth=2)

            # --- Formatting ---
            base_name = re.match(r'^[a-zA-Z_]+', uploaded_file.name).group(0).rstrip('_') if re.match(r'^[a-zA-Z_]+', uploaded_file.name) else 'subject'
            ax.set_title(f'{base_name}投手 肘関節トルクの3軸成分', fontsize=16)
            ax.set_xlabel('時間 (秒)', fontsize=12)
            ax.set_ylabel('トルク (N.mm/kg)', fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.axhline(0, color='black', linewidth=0.5)

            st.pyplot(fig)

            st.success('グラフを作成しました。下の解説を読んで、どの線が「外反トルク」に該当するかご確認ください。')

        except Exception as e:
            st.error(f'ファイルの処理中にエラーが発生しました: {e}')

else:
    st.info('サイドバーからファイルを1つアップロードしてください。')

st.divider()
st.header('【解説】外反トルク波形の特徴')
st.markdown("""
**「肘外反トルク」**は、投球動作において腕が最も後ろにしなる**最大外旋位（MER）**の周辺で、**鋭い一つのピーク**を持つ特徴的な波形を示します。
上のグラフに表示された赤・緑・青の3本線のうち、**どの色の線がこの特徴に最も近いか**、ご確認をお願いいたします。
""")
st.image('https://i.imgur.com/k2g5r2Z.png', caption='一般的な肘外反トルクの波形例（一つの鋭いピークを持つ）')
