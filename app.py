# app.py (最終形態版: シンプルモード / ダッシュボードモード切替機能付き)

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

# ==============================================================================
# ANALYSIS FUNCTIONS (These are called by the modes)
# ==============================================================================
@st.cache_data # Cache the result to avoid re-calculating
def process_all_data(_uploaded_files, side):
    """Reads uploaded files and calculates all relevant normalized metrics."""
    all_metrics_data = {
        'vel_pelvis_z': [], 'vel_thorax_z': [], 'vel_shoulder_z': [], 'vel_elbow_x': [],
        'torque_elbow_x': [], 'torque_shoulder_z': []
    }
    for uploaded_file in _uploaded_files:
        try:
            df = pd.read_excel(uploaded_file, header=[0, 1, 2])
            all_metrics_data['vel_pelvis_z'].append(normalize_curve(df[(f'{side}PelvisAngles', "Z'", 'deg/s')]))
            all_metrics_data['vel_thorax_z'].append(normalize_curve(df[(f'{side}ThoraxAngles', "Z'", 'deg/s')]))
            all_metrics_data['vel_shoulder_z'].append(normalize_curve(df[(f'{side}ShoulderAngles', "Z'", 'deg/s')]))
            all_metrics_data['vel_elbow_x'].append(normalize_curve(df[(f'{side}ElbowAngles', "X'", 'deg/s')]))
            all_metrics_data['torque_elbow_x'].append(normalize_curve(df[(f'{side}ElbowMoment', 'X', 'N.mm/kg')] / 1000.0))
            all_metrics_data['torque_shoulder_z'].append(normalize_curve(df[(f'{side}ShoulderMoment', 'Z', 'N.mm/kg')] / 1000.0))
        except Exception as e:
            st.error(f'ファイル {uploaded_file.name} の処理中にエラー: {e}')
            return None
    return all_metrics_data

def plot_simple_graph(analyzed_data, selections, title_info):
    """Plots a pre-defined graph for Simple Mode."""
    fig, ax = plt.subplots(figsize=(12, 7))
    normalized_time_axis = np.linspace(0, 100, 101)
    
    # Logic for kinetic chain plot
    if selections['analysis_type'] == '運動連鎖の評価（角速度）':
        segments = {'骨盤': 'vel_pelvis_z', '胸郭': 'vel_thorax_z', '肩(上腕)': 'vel_shoulder_z', '肘(前腕)': 'vel_elbow_x'}
        colors = {'骨盤': 'blue', '胸郭': 'green', '肩(上腕)': 'red', '肘(前腕)': 'purple'}
        y_label = '角速度 (deg/s)' if selections['graph_type'] == 'raw' else '角速度の大きさ (deg/s)'
        if selections['graph_type'] == 'raw': ax.axhline(0, color='black', linewidth=0.5)

        for name, key in segments.items():
            data = np.abs(analyzed_data[key]) if selections['graph_type'] == 'absolute' else analyzed_data[key]
            mean_curve = np.mean(data, axis=0)
            if selections['trial_mode'] == 'average':
                std_curve = np.std(data, axis=0)
                ax.fill_between(normalized_time_axis, mean_curve - std_curve, mean_curve + std_curve, color=colors[name], alpha=0.2)
            ax.plot(normalized_time_axis, mean_curve, label=name, color=colors[name], linewidth=2)
        ax.set_ylabel(y_label, fontsize=12)

    # Logic for elbow torque plot
    elif selections['analysis_type'] == '肘外反トルクの評価':
        torque_curves = analyzed_data['torque_elbow_x']
        mean_torque = np.mean(torque_curves, axis=0)
        if selections['trial_mode'] == 'average':
            std_torque = np.std(torque_curves, axis=0)
            ax.fill_between(normalized_time_axis, mean_torque - std_torque, mean_torque + std_torque, color='red', alpha=0.2)
        ax.plot(normalized_time_axis, mean_torque, label='肘外反トルク', color='red', linewidth=2)
        ax.set_ylabel('体重正規化トルク (N.m/kg)', fontsize=12)
        ax.axhline(0, color='black', linewidth=0.5)
        peak_torque_val = np.max(mean_torque)
        st.metric(label=f"ピーク時の外反トルク{'（平均）' if selections['trial_mode'] == 'average' else ''}", value=f"{peak_torque_val:.2f} N.m/kg")

    # Common formatting
    ax.set_title(title_info['custom_title'], fontsize=16)
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.legend(loc='upper left'); ax.grid(True, linestyle='--', alpha=0.7)
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200); st.download_button(label="グラフをダウンロード", data=img_buf, file_name=f"{title_info['base_name']}_graph.png", mime="image/png")

# ==============================================================================
# WEB APP LAYOUT AND LOGIC
# ==============================================================================
st.title('⚾ 投球動作 統合分析プラットフォーム')

with st.sidebar:
    st.header('ステップ1: 操作モードを選択')
    app_mode = st.selectbox("", ("シンプルモード（推奨）", "ダッシュボードモード（上級者向け）"))
    st.divider()

    st.header('ステップ2: 解析設定')
    side = st.radio('投手の利き腕を選択', ('R', 'L'), format_func=lambda x: '右投手' if x == 'R' else '左投手')
    
    # --- UI for Simple Mode ---
    if app_mode == "シンプルモード（推奨）":
        analysis_type = st.selectbox('解析の種類を選択', ('運動連鎖の評価（角速度）', '肘外反トルクの評価'))
        trial_mode = st.radio("試行数を選択", ('average', 'single'), format_func=lambda x: '3試行の平均' if x == 'average' else '1試行のみ')
        graph_type = 'absolute'
        if analysis_type == '運動連鎖の評価（角速度）':
            graph_type = st.radio('表示形式を選択', ('absolute', 'raw'), format_func=lambda x: '大きさ（絶対値）' if x == 'absolute' else '向き（生データ）')
    
    st.divider()
    st.header('ステップ3: ファイルをアップロード')
    num_files_required_text = "を3つ" if app_mode == "シンプルモード（推奨）" and trial_mode == 'average' else "を1つ以上"
    uploaded_files = st.file_uploader(f"Excelファイル{num_files_required_text}アップロード", type=['xlsx'], accept_multiple_files=True)

# ==============================================================================
# Main Panel Logic
# ==============================================================================
if uploaded_files:
    # --- Logic for Simple Mode ---
    if app_mode == "シンプルモード（推奨）":
        num_expected = 3 if trial_mode == 'average' else 1
        if len(uploaded_files) == num_expected:
            st.header(f"解析結果：{analysis_type}")
            all_data = process_all_data(uploaded_files, side)
            if all_data:
                base_name = re.match(r'^[a-zA-Z_]+', uploaded_files[0].name).group(0).rstrip('_') if re.match(r'^[a-zA-Z_]+', uploaded_files[0].name) else 'subject'
                default_title = f"{base_name}投手 - {analysis_type}"
                custom_title = st.text_input("グラフタイトルを編集:", value=default_title)
                plot_simple_graph(all_data, {'analysis_type': analysis_type, 'trial_mode': trial_mode, 'graph_type': graph_type}, {'custom_title': custom_title, 'base_name': base_name})
        else:
            st.warning(f"ファイルを{num_expected}つアップロードしてください。")

    # --- Logic for Dashboard Mode ---
    elif app_mode == "ダッシュボードモード（上級者向け）":
        st.header("対話型分析ダッシュボード")
        all_data = process_all_data(uploaded_files, side)
        if all_data:
            available_metrics = {
                '骨盤 角速度(Z)': 'vel_pelvis_z', '胸郭 角速度(Z)': 'vel_thorax_z', '肩(上腕) 角速度(Z)': 'vel_shoulder_z',
                '肘(前腕) 伸展速度(X)': 'vel_elbow_x', '肘 外反トルク(X)': 'torque_elbow_x', '肩 内旋トルク(Z)': 'torque_shoulder_z'
            }
            selected_labels = st.multiselect("グラフに表示する項目を選択（複数可）:", options=list(available_metrics.keys()), default=['骨盤 角速度(Z)', '胸郭 角速度(Z)', '肩(上腕) 角速度(Z)', '肘(前腕) 伸展速度(X)'])
            
            if selected_labels:
                fig, ax1 = plt.subplots(figsize=(12, 7))
                ax2 = ax1.twinx()
                normalized_time_axis = np.linspace(0, 100, 101)
                
                colors = plt.cm.tab10.colors
                for i, label in enumerate(selected_labels):
                    metric_key = available_metrics[label]
                    data = np.abs(all_data[metric_key])
                    mean_curve = np.mean(data, axis=0)
                    std_curve = np.std(data, axis=0)
                    
                    if 'トルク' in label:
                        ax2.plot(normalized_time_axis, mean_curve, label=label, color=colors[i], linestyle='--')
                        ax2.fill_between(normalized_time_axis, mean_curve - std_curve, mean_curve + std_curve, color=colors[i], alpha=0.1)
                    else:
                        ax1.plot(normalized_time_axis, mean_curve, label=label, color=colors[i])
                        ax1.fill_between(normalized_time_axis, mean_curve - std_curve, mean_curve + std_curve, color=colors[i], alpha=0.2)

                ax1.set_xlabel('正規化時間 (%)', fontsize=12)
                ax1.set_ylabel('角速度の大きさ (deg/s)', fontsize=12)
                ax2.set_ylabel('トルクの大きさ (N.m/kg)', fontsize=12)
                fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9))
                st.pyplot(fig)
