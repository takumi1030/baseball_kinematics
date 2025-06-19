# app.py (最終・ダッシュボード版)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import re
import os
import matplotlib.font_manager as fm

# --- Font Setup and Page Config ---
st.set_page_config(layout="wide")
font_path = 'NotoSansJP-Regular.ttf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'Noto Sans JP'
    plt.rcParams['axes.unicode_minus'] = False
else:
    st.warning(f"フォントファイル '{font_path}' が見つかりません。")

# --- Helper Function: Time Normalization ---
def normalize_curve(data_series, num_points=101):
    current_x = np.linspace(0, 100, len(data_series))
    new_x = np.linspace(0, 100, num_points)
    normalized_data = np.interp(new_x, current_x, data_series)
    return normalized_data

# --- Data Processing Function (runs once per upload) ---
@st.cache_data # Cache the result to avoid re-calculating on every interaction
def process_all_data(_uploaded_files, side):
    """
    Reads uploaded files and calculates all relevant normalized metrics (mean and std).
    The underscore on _uploaded_files tells Streamlit's cache to ignore this complex object.
    """
    all_metrics = {
        'vel_pelvis_z': [], 'vel_thorax_z': [], 'vel_shoulder_z': [], 'vel_elbow_x': [],
        'torque_elbow_x': [], 'torque_shoulder_z': []
    }
    for uploaded_file in _uploaded_files:
        try:
            df = pd.read_excel(uploaded_file, header=[0, 1, 2])
            # Velocities
            all_metrics['vel_pelvis_z'].append(normalize_curve(df[(f'{side}PelvisAngles', "Z'", 'deg/s')].abs()))
            all_metrics['vel_thorax_z'].append(normalize_curve(df[(f'{side}ThoraxAngles', "Z'", 'deg/s')].abs()))
            all_metrics['vel_shoulder_z'].append(normalize_curve(df[(f'{side}ShoulderAngles', "Z'", 'deg/s')].abs()))
            all_metrics['vel_elbow_x'].append(normalize_curve(df[(f'{side}ElbowAngles', "X'", 'deg/s')].abs()))
            # Torques (converted to N.m/kg)
            all_metrics['torque_elbow_x'].append(normalize_curve(df[(f'{side}ElbowMoment', 'X', 'N.mm/kg')] / 1000.0))
            all_metrics['torque_shoulder_z'].append(normalize_curve(df[(f'{side}ShoulderMoment', 'Z', 'N.mm/kg')] / 1000.0))
        except Exception as e:
            st.error(f'ファイル {uploaded_file.name} の処理中にエラー: {e}')
            return None

    # Calculate mean and std for each metric
    processed_data = {}
    for key, curves in all_metrics.items():
        if curves:
            processed_data[key] = {
                'mean': np.mean(curves, axis=0),
                'std': np.std(curves, axis=0)
            }
    return processed_data

# ==============================================================================
# Main App UI and Logic
# ==============================================================================
st.title('⚾ 投球動作 対話型分析ダッシュボード')
st.write('一度にすべての解析を行い、見たい項目を自由に組み合わせてグラフに表示できます。')

with st.sidebar:
    st.header('ステップ1: 解析設定')
    side = st.radio('投手の利き腕を選択', ('R', 'L'), format_func=lambda x: '右投手' if x == 'R' else '左投手')
    
    st.header('ステップ2: ファイルをアップロード')
    uploaded_files = st.file_uploader(f"解析したい{side}投手のExcelファイルを3つアップロードしてください", type=['xlsx'], accept_multiple_files=True)
    st.info('解析したい被験者1名分の、3試行のデータ（Excelファイル）を一度に選択してください。')

if uploaded_files:
    if len(uploaded_files) == 3:
        # --- Run the one-time comprehensive analysis ---
        analyzed_data = process_all_data(uploaded_files, side)

        if analyzed_data:
            st.header("ステップ3: グラフのカスタマイズ")
            
            # --- Interactive UI for Plotting ---
            available_metrics = {
                '骨盤 角速度 (Z)': 'vel_pelvis_z',
                '胸郭 角速度 (Z)': 'vel_thorax_z',
                '肩(上腕) 角速度 (Z)': 'vel_shoulder_z',
                '肘(前腕) 伸展速度 (X)': 'vel_elbow_x',
                '肘 外反トルク (X)': 'torque_elbow_x',
                '肩 内旋トルク (Z)': 'torque_shoulder_z'
            }
            
            cols = st.columns(2)
            with cols[0]:
                selected_labels = st.multiselect(
                    "グラフに表示する項目を選択（複数可）:",
                    options=list(available_metrics.keys()),
                    default=['骨盤 角速度 (Z)', '胸郭 角速度 (Z)', '肩(上腕) 角速度 (Z)', '肘(前腕) 伸展速度 (X)']
                )
            with cols[1]:
                custom_title = st.text_input("グラフタイトルを編集:", value=f"{re.match(r'^[a-zA-Z_]+', uploaded_files[0].name).group(0).rstrip('_')}投手 動作分析")

            # --- Dynamic Plotting ---
            if selected_labels:
                fig, ax = plt.subplots(figsize=(12, 7))
                ax2 = ax.twinx() # Create a second y-axis
                normalized_time_axis = np.linspace(0, 100, 101)
                
                # Assign colors and axes
                colors = plt.cm.tab10.colors
                color_idx = 0
                ax1_labels, ax2_labels = [], []

                for label in selected_labels:
                    metric_key = available_metrics[label]
                    data = analyzed_data[metric_key]
                    
                    if 'トルク' in label: # Plot torque on the right y-axis (ax2)
                        p = ax2.plot(normalized_time_axis, data['mean'], label=label, color=colors[color_idx], linestyle='--')
                        ax2.fill_between(normalized_time_axis, data['mean'] - data['std'], data['mean'] + data['std'], color=colors[color_idx], alpha=0.1)
                        ax2_labels.append(p[0])
                    else: # Plot velocity on the left y-axis (ax1)
                        p = ax.plot(normalized_time_axis, data['mean'], label=label, color=colors[color_idx])
                        ax.fill_between(normalized_time_axis, data['mean'] - data['std'], data['mean'] + data['std'], color=colors[color_idx], alpha=0.2)
                        ax1_labels.append(p[0])
                    color_idx += 1
                
                # --- Formatting Axes and Legend ---
                ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
                ax.set_title(custom_title, fontsize=16)
                ax.grid(True, linestyle='--', which='major', alpha=0.7)
                
                # Only show y-axis labels if there is data for them
                if ax1_labels:
                    ax.set_ylabel('角速度の大きさ (deg/s)', fontsize=12, color=colors[0])
                    ax.tick_params(axis='y', labelcolor=colors[0])
                if ax2_labels:
                    ax2.set_ylabel('トルクの大きさ (N.m/kg)', fontsize=12, color=colors[1])
                    ax2.tick_params(axis='y', labelcolor=colors[1])
                    ax2.spines['right'].set_color(colors[1])
                    ax2.spines['left'].set_color(colors[0])
                
                # Combine legends from both axes
                all_labels = ax1_labels + ax2_labels
                ax.legend(all_labels, [l.get_label() for l in all_labels], loc='upper left')

                st.pyplot(fig)
                
                # --- Download Button ---
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', dpi=200)
                st.download_button(label="グラフをダウンロード", data=img_buf, file_name="custom_analysis_graph.png", mime="image/png")
            else:
                st.info("グラフに表示する項目を1つ以上選択してください。")
    else:
        st.warning(f"ファイルの数が正しくありません。3つのファイルが必要です。")
