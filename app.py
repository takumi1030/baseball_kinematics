# app.py (最終統合版：運動連鎖＋肘トルク評価)

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
def run_kinetic_chain_analysis(uploaded_files, side, graph_type):
    with st.spinner('角速度データを処理中...'):
        all_pelvis_curves, all_thorax_curves, all_shoulder_curves, all_elbow_curves = [], [], [], []
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1, 2])
                # Extract data based on side and correct axis
                data_dict = {
                    'pelvis': df[(f'{side}PelvisAngles', "Z'", 'deg/s')],
                    'thorax': df[(f'{side}ThoraxAngles', "Z'", 'deg/s')],
                    'shoulder': df[(f'{side}ShoulderAngles', "Z'", 'deg/s')],
                    'elbow': df[(f'{side}ElbowAngles', "X'", 'deg/s')]
                }
                if graph_type == 'absolute':
                    for key in data_dict: data_dict[key] = data_dict[key].abs()
                
                all_pelvis_curves.append(normalize_curve(data_dict['pelvis']))
                all_thorax_curves.append(normalize_curve(data_dict['thorax']))
                all_shoulder_curves.append(normalize_curve(data_dict['shoulder']))
                all_elbow_curves.append(normalize_curve(data_dict['elbow']))
            except Exception as e:
                st.error(f'ファイル {uploaded_file.name} の処理中にエラー: {e}')
                return

    st.success('データ処理が完了しました。')
    
    # --- Averaging & Plotting ---
    means = {'pelvis': np.mean(all_pelvis_curves, axis=0), 'thorax': np.mean(all_thorax_curves, axis=0), 'shoulder': np.mean(all_shoulder_curves, axis=0), 'elbow': np.mean(all_elbow_curves, axis=0)}
    stds = {'pelvis': np.std(all_pelvis_curves, axis=0), 'thorax': np.std(all_thorax_curves, axis=0), 'shoulder': np.std(all_shoulder_curves, axis=0), 'elbow': np.std(all_elbow_curves, axis=0)}

    fig, ax = plt.subplots(figsize=(12, 7))
    normalized_time_axis = np.linspace(0, 100, 101)
    segments = {'骨盤': 'pelvis', '胸郭': 'thorax', '肩(上腕)': 'shoulder', '肘(前腕)': 'elbow'}
    colors = {'骨盤': 'blue', '胸郭': 'green', '肩(上腕)': 'red', '肘(前腕)': 'purple'}

    for name, key in segments.items():
        ax.plot(normalized_time_axis, means[key], label=name, color=colors[name], linewidth=2)
        ax.fill_between(normalized_time_axis, means[key] - stds[key], means[key] + stds[key], color=colors[name], alpha=0.2)
    
    # --- Formatting, Title, Download ---
    base_name = re.match(r'^[a-zA-Z_]+', uploaded_files[0].name).group(0).rstrip('_') if re.match(r'^[a-zA-Z_]+', uploaded_files[0].name) else 'subject'
    title_suffix = '（絶対値）' if graph_type == 'absolute' else '（生データ）'
    y_label = '角速度の大きさ (deg/s)' if graph_type == 'absolute' else '角速度 (deg/s)'
    if graph_type == 'raw': ax.axhline(0, color='black', linewidth=0.5)
    
    custom_title = st.text_input("グラフタイトルを編集:", value=f'{base_name}投手 平均角速度の運動連鎖 {title_suffix}')
    ax.set_title(custom_title, fontsize=16)
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    st.pyplot(fig)
    
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200)
    st.download_button(label="グラフをダウンロード", data=img_buf, file_name=f"{base_name}_velocity_chain.png", mime="image/png")

# ==============================================================================
# ANALYSIS FUNCTION 2: ELBOW VALGUS TORQUE
# ==============================================================================
def run_elbow_torque_analysis(uploaded_files, side):
    with st.spinner('肘トルクデータを処理中...'):
        all_torque_curves = []
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1, 2])
                # Extract Elbow Moment X-axis and convert units from N.mm/kg to N.m/kg
                torque_nm_per_kg = df[(f'{side}ElbowMoment', 'X', 'N.mm/kg')] / 1000.0
                all_torque_curves.append(normalize_curve(torque_nm_per_kg))
            except Exception as e:
                st.error(f'ファイル {uploaded_file.name} の処理中にエラー: {e}')
                return

    st.success('データ処理が完了しました。')
    
    # --- Averaging & Plotting ---
    mean_torque = np.mean(all_torque_curves, axis=0)
    std_torque = np.std(all_torque_curves, axis=0)
    peak_torque_val = np.max(mean_torque)
    peak_torque_time = np.linspace(0, 100, 101)[np.argmax(mean_torque)]

    fig, ax = plt.subplots(figsize=(12, 7))
    normalized_time_axis = np.linspace(0, 100, 101)

    ax.plot(normalized_time_axis, mean_torque, label='平均 肘外反トルク', color='red', linewidth=2)
    ax.fill_between(normalized_time_axis, mean_torque - std_torque, mean_torque + std_torque, color='red', alpha=0.2)
    
    # --- Formatting, Title, Download ---
    base_name = re.match(r'^[a-zA-Z_]+', uploaded_files[0].name).group(0).rstrip('_') if re.match(r'^[a-zA-Z_]+', uploaded_files[0].name) else 'subject'
    custom_title = st.text_input("グラフタイトルを編集:", value=f'{base_name}投手 平均 肘外反トルク')
    ax.set_title(custom_title, fontsize=16)
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.set_ylabel('体重正規化トルク (N.m/kg)', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.axhline(0, color='black', linewidth=0.5)

    st.pyplot(fig)
    
    # --- Display Peak Value ---
    st.metric(label="ピーク時の平均外反トルク（体重あたり）", value=f"{peak_torque_val:.2f} N.m/kg")
    st.caption(f"ピーク到達時間: 正規化時間 {peak_torque_time:.1f}% 地点")

    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200)
    st.download_button(label="グラフをダウンロード", data=img_buf, file_name=f"{base_name}_elbow_torque.png", mime="image/png")

# ==============================================================================
# WEB APP LAYOUT AND LOGIC
# ==============================================================================
st.title('⚾ 投球動作 統合分析プラットフォーム')

with st.sidebar:
    st.header('ステップ1: 解析の種類を選択')
    analysis_type = st.selectbox(
        'どの解析を実行しますか？',
        ('運動連鎖の評価（角速度）', '肘外反トルクの評価')
    )
    st.divider()

    st.header('ステップ2: 解析設定')
    side = st.radio('投手の利き腕を選択', ('R', 'L'), format_func=lambda x: '右投手' if x == 'R' else '左投手')
    
    # Show graph type option only for kinetic chain analysis
    graph_type = 'absolute'
    if analysis_type == '運動連鎖の評価（角速度）':
        graph_type = st.radio('グラフの表示形式を選択', ('absolute', 'raw'), format_func=lambda x: '大きさ（絶対値）' if x == 'absolute' else '向き（生データ）')

    st.divider()
    st.header('ステップ3: ファイルをアップロード')
    uploaded_files = st.file_uploader(
        f"解析したい{side}投手のExcelファイルを3つアップロードしてください",
        type=['xlsx'],
        accept_multiple_files=True
    )
    st.info('解析したい被験者1名分の、3試行のデータ（Excelファイル）を一度に選択してください。')

# --- Main Panel to Run Analysis ---
if uploaded_files:
    if len(uploaded_files) == 3:
        st.header(f"解析結果：{analysis_type}")
        if analysis_type == '運動連鎖の評価（角速度）':
            run_kinetic_chain_analysis(uploaded_files, side, graph_type)
        elif analysis_type == '肘外反トルクの評価':
            run_elbow_torque_analysis(uploaded_files, side)
    else:
        st.warning('ファイルを3つアップロードしてください。')
