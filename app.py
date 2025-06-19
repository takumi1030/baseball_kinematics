# app.py (最終アップグレード版: 1試行/平均の選択機能付き)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import re
import os
import matplotlib.font_manager as fm

# --- Font Setup ---
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
# ANALYSIS FUNCTION 1: KINETIC CHAIN (ANGULAR VELOCITY)
# ==============================================================================
def run_kinetic_chain_analysis(uploaded_files, side, graph_type, trial_mode):
    with st.spinner('角速度データを処理中...'):
        all_pelvis_curves, all_thorax_curves, all_shoulder_curves, all_elbow_curves = [], [], [], []
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1, 2])
                data_dict = {'pelvis': df[(f'{side}PelvisAngles', "Z'", 'deg/s')], 'thorax': df[(f'{side}ThoraxAngles', "Z'", 'deg/s')], 'shoulder': df[(f'{side}ShoulderAngles', "Z'", 'deg/s')], 'elbow': df[(f'{side}ElbowAngles', "X'", 'deg/s')]}
                if graph_type == 'absolute':
                    for key in data_dict: data_dict[key] = data_dict[key].abs()
                all_pelvis_curves.append(normalize_curve(data_dict['pelvis']))
                all_thorax_curves.append(normalize_curve(data_dict['thorax']))
                all_shoulder_curves.append(normalize_curve(data_dict['shoulder']))
                all_elbow_curves.append(normalize_curve(data_dict['elbow']))
            except Exception as e:
                st.error(f'ファイル {uploaded_file.name} の処理中にエラー: {e}'); return

    st.success('データ処理が完了しました。')
    
    # --- Averaging & Plotting ---
    fig, ax = plt.subplots(figsize=(12, 7))
    normalized_time_axis = np.linspace(0, 100, 101)
    segments = {'骨盤': 'pelvis', '胸郭': 'thorax', '肩(上腕)': 'shoulder', '肘(前腕)': 'elbow'}
    colors = {'骨盤': 'blue', '胸郭': 'green', '肩(上腕)': 'red', '肘(前腕)': 'purple'}
    curves = {'pelvis': all_pelvis_curves, 'thorax': all_thorax_curves, 'shoulder': all_shoulder_curves, 'elbow': all_elbow_curves}

    for name, key in segments.items():
        if trial_mode == 'average':
            mean_curve = np.mean(curves[key], axis=0)
            std_curve = np.std(curves[key], axis=0)
            ax.plot(normalized_time_axis, mean_curve, label=name, color=colors[name], linewidth=2)
            ax.fill_between(normalized_time_axis, mean_curve - std_curve, mean_curve + std_curve, color=colors[name], alpha=0.2)
        else: # single trial
            ax.plot(normalized_time_axis, curves[key][0], label=name, color=colors[name], linewidth=2)
    
    # --- Formatting, Title, Download ---
    base_name = re.match(r'^[a-zA-Z_]+', uploaded_files[0].name).group(0).rstrip('_') if re.match(r'^[a-zA-Z_]+', uploaded_files[0].name) else 'subject'
    title_mode_suffix = ' 平均' if trial_mode == 'average' else ''
    title_type_suffix = '（絶対値）' if graph_type == 'absolute' else '（生データ）'
    y_label = '角速度の大きさ (deg/s)' if graph_type == 'absolute' else '角速度 (deg/s)'
    if graph_type == 'raw': ax.axhline(0, color='black', linewidth=0.5)
    
    default_title = f'{base_name}投手{title_mode_suffix}角速度の運動連鎖 {title_type_suffix}'
    custom_title = st.text_input("グラフタイトルを編集:", value=default_title)
    ax.set_title(custom_title, fontsize=16)
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200); st.download_button(label="グラフをダウンロード", data=img_buf, file_name=f"{base_name}_velocity_chain.png", mime="image/png")

# ==============================================================================
# ANALYSIS FUNCTION 2: ELBOW VALGUS TORQUE
# ==============================================================================
def run_elbow_torque_analysis(uploaded_files, side, trial_mode):
    with st.spinner('肘トルクデータを処理中...'):
        all_torque_curves = []
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1, 2])
                torque_nm_per_kg = df[(f'{side}ElbowMoment', 'X', 'N.mm/kg')] / 1000.0
                all_torque_curves.append(normalize_curve(torque_nm_per_kg))
            except Exception as e:
                st.error(f'ファイル {uploaded_file.name} の処理中にエラー: {e}'); return

    st.success('データ処理が完了しました。')
    
    # --- Averaging & Plotting ---
    fig, ax = plt.subplots(figsize=(12, 7))
    normalized_time_axis = np.linspace(0, 100, 101)
    
    if trial_mode == 'average':
        mean_torque = np.mean(all_torque_curves, axis=0)
        std_torque = np.std(all_torque_curves, axis=0)
        ax.plot(normalized_time_axis, mean_torque, label='平均 肘外反トルク', color='red', linewidth=2)
        ax.fill_between(normalized_time_axis, mean_torque - std_torque, mean_torque + std_torque, color='red', alpha=0.2)
        peak_torque_val = np.max(mean_torque)
    else: # single trial
        mean_torque = all_torque_curves[0]
        ax.plot(normalized_time_axis, mean_torque, label='肘外反トルク', color='red', linewidth=2)
        peak_torque_val = np.max(mean_torque)
        
    peak_torque_time = normalized_time_axis[np.argmax(mean_torque)]
    
    # --- Formatting, Title, Download ---
    base_name = re.match(r'^[a-zA-Z_]+', uploaded_files[0].name).group(0).rstrip('_') if re.match(r'^[a-zA-Z_]+', uploaded_files[0].name) else 'subject'
    title_mode_suffix = ' 平均' if trial_mode == 'average' else ''
    custom_title = st.text_input("グラフタイトルを編集:", value=f'{base_name}投手{title_mode_suffix} 肘外反トルク')
    ax.set_title(custom_title, fontsize=16)
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.set_ylabel('体重正規化トルク (N.m/kg)', fontsize=12)
    ax.legend(fontsize=10); ax.grid(True, linestyle='--', alpha=0.6); ax.axhline(0, color='black', linewidth=0.5)
    
    st.pyplot(fig)
    st.metric(label=f"ピーク時の外反トルク{'（平均）' if trial_mode == 'average' else ''}", value=f"{peak_torque_val:.2f} N.m/kg")
    st.caption(f"ピーク到達時間: 正規化時間 {peak_torque_time:.1f}% 地点")
    
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200); st.download_button(label="グラフをダウンロード", data=img_buf, file_name=f"{base_name}_elbow_torque.png", mime="image/png")

# ==============================================================================
# WEB APP LAYOUT AND LOGIC
# ==============================================================================
st.title('⚾ 投球動作 統合分析プラットフォーム')

with st.sidebar:
    st.header('ステップ1: 解析の種類を選択')
    analysis_type = st.selectbox('どの解析を実行しますか？', ('運動連鎖の評価（角速度）', '肘外反トルクの評価'))
    
    # ★★★ ここが追加された機能です ★★★
    trial_mode = st.radio("試行数を選択", ('average', 'single'), index=0, format_func=lambda x: '3試行の平均' if x == 'average' else '1試行のみ')
    
    st.divider()
    st.header('ステップ2: 解析設定')
    side = st.radio('投手の利き腕を選択', ('R', 'L'), format_func=lambda x: '右投手' if x == 'R' else '左投手')
    
    graph_type = 'absolute'
    if analysis_type == '運動連鎖の評価（角速度）':
        graph_type = st.radio('グラフの表示形式を選択', ('absolute', 'raw'), format_func=lambda x: '大きさ（絶対値）' if x == 'absolute' else '向き（生データ）')

    st.divider()
    st.header('ステップ3: ファイルをアップロード')
    uploaded_files = st.file_uploader("Excelファイルをアップロード", type=['xlsx'], accept_multiple_files=True)
    
    # ★★★ ここが変更点です ★★★
    if trial_mode == 'single':
        st.info('解析したいファイルを1つだけアップロードしてください。')
    else:
        st.info('解析したい被験者1名分の、3試行のデータ（Excelファイル）を一度に選択してください。')

# --- Main Panel to Run Analysis ---
if uploaded_files:
    num_files_required = 1 if trial_mode == 'single' else 3
    if len(uploaded_files) == num_files_required:
        st.header(f"解析結果：{analysis_type}")
        if analysis_type == '運動連鎖の評価（角速度）':
            run_kinetic_chain_analysis(uploaded_files, side, graph_type, trial_mode)
        elif analysis_type == '肘外反トルクの評価':
            run_elbow_torque_analysis(uploaded_files, side, trial_mode)
    else:
        st.warning(f"ファイルの数が正しくありません。現在「{'1試行のみ' if trial_mode == 'single' else '3試行の平均'}」モードが選択されています。必要なファイル数は{num_files_required}つです。")
