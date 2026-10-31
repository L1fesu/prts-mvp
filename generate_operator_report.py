#!/usr/bin/env python3
"""Generate a static operator-frequency report from zoot-plus-store JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def iter_json_files(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*.json") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )


def load_html_records(paths: list[Path], root: Path) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    records: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []
    for path in paths:
        if not path.stem.isdecimal():
            continue
        try:
            stage_id = int(path.stem)
            if stage_id < 0:
                continue
            data: Any = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("JSON 顶层不是对象")
            opers = data.get("opers")
            if not isinstance(opers, list):
                raise ValueError("缺少有效的顶层 opers 数组")
            names: list[str] = []
            for index, item in enumerate(opers):
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    raise ValueError(f"顶层 opers 第 {index + 1} 项没有有效 name")
                name = item["name"].strip()
                if name:
                    names.append(name)
            relative = path.relative_to(root).parts
            records.append({"id": stage_id, "type": relative[0] if relative else "未分类", "names": names})
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            skipped.append((str(path), str(exc)))
    return records, skipped


def load_operator_metadata(path: Path) -> dict[str, dict[str, Any]]:
    data: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("干员数据 JSON 顶层必须是数组")

    operators: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"干员数据第 {index + 1} 项不是对象")
        name = item.get("name")
        profession = item.get("profession")
        rarity = item.get("rarity")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"干员数据第 {index + 1} 项没有有效 name")
        if not isinstance(profession, str) or not profession.strip():
            raise ValueError(f"干员数据第 {index + 1} 项没有有效 profession")
        if isinstance(rarity, bool) or not isinstance(rarity, int) or not 1 <= rarity <= 6:
            raise ValueError(f"干员数据第 {index + 1} 项 rarity 必须是 1 到 6 的整数")
        operators[name.strip()] = {"profession": profession.strip(), "rarity": rarity}
    return operators


def write_html_report(
    output: Path,
    records: list[dict[str, Any]],
    operator_metadata: dict[str, dict[str, Any]],
) -> None:
    # Store operator names once and refer to them by numeric IDs in each job.
    # This substantially reduces the embedded payload when names repeat often.
    operator_names = list(operator_metadata)
    operator_ids = {name: index for index, name in enumerate(operator_names)}
    for record in records:
        for name in record["names"]:
            if name not in operator_ids:
                operator_ids[name] = len(operator_names)
                operator_names.append(name)
    compact_records = [
        [record["id"], record["type"], [operator_ids[name] for name in record["names"]]]
        for record in records
    ]
    compact_metadata = [
        ([operator_metadata[name]["profession"], operator_metadata[name]["rarity"]]
         if name in operator_metadata else None)
        for name in operator_names
    ]
    payload = json.dumps(compact_records, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    names_payload = json.dumps(operator_names, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    operator_payload = json.dumps(compact_metadata, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PRTS MVP</title>
<link rel="icon" type="image/png" href="favicon.png">
<style>
  :root {{ color-scheme: light; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background: #f2f4f7; color: #252a32; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-width: 320px; background: #f2f4f7; }}
  main {{ max-width: 1240px; margin: 0 auto; padding: 26px 24px 52px; }}
  .site-header {{ max-width: 1240px; margin: 0 auto; padding: 25px 24px 18px; border-bottom: 1px solid #dce2e8; }}
  .site-title {{ margin: 0; color: #29313a; font-size: 24px; font-weight: 700; line-height: 1.2; }}
  .panel {{ background: #fff; border: 1px solid #e1e5ea; border-radius: 4px; padding: 22px 24px; margin-bottom: 18px; box-shadow: 0 2px 8px #1826360b; }}
  .filters {{ border-top: 3px solid #2385c5; }}
  .row {{ display: flex; flex-wrap: wrap; gap: 12px 16px; align-items: center; }}
  .section-label {{ color: #303944; font-size: 15px; font-weight: 700; min-width: 70px; }}
  label {{ color: #66717e; font-size: 13px; }}
  input[type=number] {{ width: 132px; padding: 9px 10px; color: #29313a; background: #fff; border: 1px solid #cbd3dc; border-radius: 3px; font-size: 14px; outline: none; }}
  input[type=number]:focus {{ border-color: #2385c5; box-shadow: 0 0 0 2px #2385c51f; }}
  button {{ padding: 9px 16px; border: 1px solid #2385c5; border-radius: 3px; background: #2385c5; color: #fff; font-weight: 600; cursor: pointer; transition: .15s ease; }}
  button:hover {{ background: #176ea8; border-color: #176ea8; }}
  .range-preset {{ padding: 8px 14px; background: #fff; border-color: #cbd3dc; color: #566372; }}
  .range-preset:hover, .range-preset.is-active {{ background: #e9f4fb; border-color: #2385c5; color: #176ea8; }}
  .explanation {{ color: #8a95a2; font-size: 12px; line-height: 1.7; margin-top: 8px; }}
  .explanation p {{ margin: 2px 0; }}
  .types {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
  .filter-list {{ display: grid; gap: 14px; margin-top: 18px; }}
  .filter-row {{ display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 12px; align-items: start; }}
  .filter-row .section-label {{ padding-top: 7px; }}
  .filter-row .types {{ margin-top: 0; }}
  .filter-options {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}
  .filter-options .types {{ margin-top: 0; }}
  .filter-actions {{ display: flex; gap: 6px; order: -1; }}
  .filter-actions button {{ height: 34px; padding: 0 10px; border-color: #cbd3dc; background: #fff; color: #586675; font-size: 12px; }}
  .filter-actions button:hover {{ background: #e9f4fb; border-color: #2385c5; color: #176ea8; }}
  .types label {{ display: inline-flex; align-items: center; gap: 7px; height: 34px; padding: 0 11px; background: #f7f9fb; border: 1px solid #d8dee6; color: #5b6775; cursor: pointer; transition: .15s ease; }}
  .types label:has(input:checked) {{ border-color: #2385c5; background: #e9f4fb; color: #176ea8; box-shadow: inset 0 -2px #2385c5; }}
  .types input {{ accent-color: #2385c5; }}
  .types label:has(input:disabled) {{ background: #f2f4f7; border-color: #e3e7ec; color: #a8b2bd; cursor: not-allowed; box-shadow: none; }}
  .types label:has(input:disabled) input {{ accent-color: #a8b2bd; }}
  .plain-button {{ padding: 8px 14px; background: #fff; border-color: #cbd3dc; color: #566372; }}
  .plain-button:hover {{ background: #e9f4fb; border-color: #2385c5; color: #176ea8; }}
  .owner-status {{ color: #8a95a2; font-size: 12px; }}
  .owner-status.is-error {{ color: #c0392b; }}
  #summary {{ color: #7a8694; font-size: 13px; margin-top: 18px; padding-top: 14px; border-top: 1px solid #e6e9ed; }}
  .chart-head {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px; }}
  .chart-note {{ color: #8a95a2; font-size: 12px; }}
  .table-head {{ display: grid; grid-template-columns: minmax(110px, 190px) 1fr 78px; gap: 12px; align-items: center; padding: 0 0 11px; border-bottom: 1px solid #dce2e8; color: #6d7885; font-size: 12px; }}
  .table-head .operator-label {{ text-align: right; }}
  .count-label {{ grid-column: 3; color: #526171; font-weight: 600; }}
  .bar-row {{ display: grid; grid-template-columns: minmax(110px, 190px) 1fr 78px; gap: 12px; align-items: center; min-height: 36px; margin: 0; border-bottom: 1px solid #edf0f3; }}
  .bar-row:hover {{ background: #f7fafc; }}
  .name {{ color: #35404c; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }}
  .name a {{ color: inherit; text-decoration: none; }}
  .name a:hover {{ color: #176ea8; text-decoration: underline; text-underline-offset: 2px; }}
  .track {{ height: 12px; background: #edf1f5; border: 0; overflow: hidden; }}
  .bar {{ height: 100%; background: #2385c5; min-width: 2px; }}
  .value {{ font-variant-numeric: tabular-nums; color: #3f4c5a; font-weight: 700; }}
  .load-more-wrap {{ display: flex; justify-content: flex-end; margin-top: 18px; }}
  .load-more {{ padding: 8px 14px; background: #fff; border-color: #cbd3dc; color: #586675; }}
  .load-more:hover {{ background: #e9f4fb; border-color: #2385c5; color: #176ea8; }}
  .empty {{ color: #8a95a2; padding: 50px 0; text-align: center; }}
  footer {{ max-width: 1240px; margin: 0 auto; padding: 22px 24px 32px; border-top: 1px solid #dce2e8; color: #89939e; font-size: 12px; line-height: 1.8; }}
  footer p {{ margin: 3px 0; }}
  footer a {{ color: #52718c; text-decoration-color: #2385c5; text-underline-offset: 3px; }}
  footer a:hover {{ color: #176ea8; }}
  @media (max-width: 640px) {{ .site-header {{ padding: 20px 12px 14px; }} .site-title {{ font-size: 21px; }} main {{ padding: 18px 12px 34px; }} .bar-row, .table-head {{ grid-template-columns: minmax(82px, 110px) 1fr 56px; gap: 7px; }} .name {{ font-size: 12px; }} .panel {{ padding: 17px 14px; }} footer {{ padding: 20px 12px 28px; }} }}
</style>
</head>
<body>
<header class="site-header"><h1 class="site-title">PRTS MVP</h1></header>
<main>
  <section class="panel filters">
    <div class="row">
      <span class="section-label">作业范围</span>
      <label>最小值 <input id="minId" type="number" min="0" step="1"></label>
      <label>最大值 <input id="maxId" type="number" min="0" step="1"></label>
      <button class="range-preset" data-range="all" type="button"></button>
      <button class="range-preset" data-range="new" type="button"></button>
      <button class="range-preset" data-range="latest" type="button"></button>
    </div>
    <div class="filter-list">
      <div class="filter-row"><span class="section-label">规则</span><div class="types mode-options"><label><input id="dedupeStage" type="checkbox"> 同关去重</label><label><input id="onlySolo" type="checkbox"> 只看单核</label><label><input id="bestCombo" type="checkbox"> 最佳组合</label></div></div>
      <div class="filter-row"><span class="section-label">场景</span><div class="filter-options"><div class="filter-actions"><button type="button" data-filter-target="types" data-filter-value="true">全选</button><button type="button" data-filter-target="types" data-filter-value="false">清空</button></div><div id="types" class="types"></div></div></div>
      <div class="filter-row"><span class="section-label">星级</span><div class="filter-options"><div class="filter-actions"><button type="button" data-filter-target="rarities" data-filter-value="true">全选</button><button type="button" data-filter-target="rarities" data-filter-value="false">清空</button></div><div id="rarities" class="types"></div></div></div>
      <div class="filter-row"><span class="section-label">职业</span><div class="filter-options"><div class="filter-actions"><button type="button" data-filter-target="professions" data-filter-value="true">全选</button><button type="button" data-filter-target="professions" data-filter-value="false">清空</button></div><div id="professions" class="types"></div></div></div>
      <div class="filter-row"><span class="section-label">是否拥有</span><div class="filter-options"><div id="ownership" class="types"><label><input type="radio" name="ownership" value="all" checked> 不限</label><label><input type="radio" name="ownership" value="owned" disabled> 已拥有</label><label><input type="radio" name="ownership" value="unowned" disabled> 未拥有</label></div><button id="pickOwnerFile" class="plain-button" type="button">选择文件</button><input id="ownerFile" type="file" accept=".json,application/json" hidden><button id="clearOwners" class="plain-button" type="button" hidden>清除</button><span id="ownerStatus" class="owner-status"></span></div></div>
    </div>
    <div id="summary"></div>
    <div class="explanation">
      <p>* 数值越大，通常意味着作业越新。</p>
      <p>* 只看单核：将3星干员视为辅助位，作业中仅有一名3星及以上干员。</p>
      <p>* 最佳组合仅统计3星及以上干员。</p>
      <p>* 「已拥有/未拥有」需先上传 MAA 导出的干员数据，文件只在浏览器本地解析，不会上传到任何服务器。</p>
    </div>
  </section>
  <section class="panel"><div class="chart-head"><span></span><span id="rankingNote" class="chart-note"></span></div><div class="table-head"><span class="operator-label">干员</span><span></span><span id="countLabel" class="count-label">出现次数</span></div><div id="chart"></div><div class="load-more-wrap"><button id="loadAll" class="load-more" type="button"></button></div></section>
</main>
<footer>
  <p>项目仓库：<a href="https://github.com/L1fesu/prts-mvp" target="_blank" rel="noopener noreferrer">L1fesu/prts-mvp</a>。</p>
  <p>数据来源：<a href="https://github.com/ZOOT-Plus/zoot-plus-store" target="_blank" rel="noopener noreferrer">ZOOT-Plus/zoot-plus-store</a> 项目公开收录的作业 JSON 文件。</p>
  <p>本页面根据作业 JSON 文件名及目录类型汇总干员出现次数，统计结果仅供信息参考；数据内容及其准确性以来源项目为准。</p>
  <p>本页面为玩家制作的非官方统计工具，与鹰角网络及《明日方舟》官方无关。相关名称、标识及内容的权利归其各自权利人所有。</p>
</footer>
<script>
const records = {payload};
const operatorNames = {names_payload};
const operatorMetadata = {operator_payload};
const maxDataId = records.reduce((m, r) => Math.max(m, r[0]), 0);
const minInput = document.getElementById('minId');
const maxInput = document.getElementById('maxId');
const typesBox = document.getElementById('types');
const raritiesBox = document.getElementById('rarities');
const professionsBox = document.getElementById('professions');
const dedupeStage = document.getElementById('dedupeStage');
const onlySolo = document.getElementById('onlySolo');
const bestCombo = document.getElementById('bestCombo');
const summary = document.getElementById('summary');
const chart = document.getElementById('chart');
const loadAll = document.getElementById('loadAll');
const rankingNote = document.getElementById('rankingNote');
const countLabel = document.getElementById('countLabel');
let showAll = false;
const ownershipBox = document.getElementById('ownership');
const ownerFile = document.getElementById('ownerFile');
const ownerStatus = document.getElementById('ownerStatus');
const clearOwners = document.getElementById('clearOwners');
const pickOwnerFile = document.getElementById('pickOwnerFile');
const OWNER_STORAGE_KEY = 'prts-mvp-owners-v1';
let ownedNames = null;
let ownedCount = 0;
const rangeButtons = {{ all: document.querySelector('[data-range="all"]'), new: document.querySelector('[data-range="new"]'), latest: document.querySelector('[data-range="latest"]') }};
rangeButtons.all.textContent = `全部(0-${{maxDataId}})`;
rangeButtons.new.textContent = `较新(${{Math.floor(maxDataId / 2)}}-${{maxDataId}})`;
rangeButtons.latest.textContent = `最新(${{Math.floor(maxDataId * 3 / 4)}}-${{maxDataId}})`;
function addOptions(box, values, format = value => value) {{
  values.forEach(value => {{
    const label = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'checkbox'; input.value = String(value); input.checked = true; input.addEventListener('change', update);
    label.append(input, document.createTextNode(' ' + format(value))); box.append(label);
  }});
}}
const types = [...new Set(records.map(r => r[1]))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
const professions = ['先锋', '近卫', '重装', '狙击', '术师', '医疗', '辅助', '特种'];
addOptions(typesBox, types);
addOptions(raritiesBox, [6, 5, 4, 3, 2, 1], rarity => `${{rarity}}⭐️`);
addOptions(professionsBox, professions);
document.querySelectorAll('[data-filter-target]').forEach(button => button.addEventListener('click', () => {{
  const box = document.getElementById(button.dataset.filterTarget);
  const checked = button.dataset.filterValue === 'true';
  box.querySelectorAll('input[type="checkbox"]').forEach(input => {{ input.checked = checked; }});
  showAll = false;
  update();
}}));
function setRange(minimum, preset) {{
  minInput.value = minimum; maxInput.value = maxDataId;
  document.querySelectorAll('.range-preset').forEach(button => button.classList.toggle('is-active', button.dataset.range === preset));
  showAll = false; update();
}}
function checkedValues(box) {{ return new Set([...box.querySelectorAll('input:checked')].map(input => input.value)); }}
function matchesOperator(name, selectedRarities, selectedProfessions) {{
  const metadata = operatorMetadata[name];
  return Boolean(metadata && selectedRarities.has(String(metadata[1])) && selectedProfessions.has(metadata[0]) && matchesOwnership(name));
}}
function update() {{
  let min = Number.parseInt(minInput.value, 10); let max = Number.parseInt(maxInput.value, 10);
  if (!Number.isFinite(min)) min = 0; if (!Number.isFinite(max)) max = maxDataId;
  min = Math.max(0, Math.min(min, maxDataId)); max = Math.max(0, Math.min(max, maxDataId));
  if (min > max) [min, max] = [max, min];
  const chosenTypes = checkedValues(typesBox);
  const chosenRarities = checkedValues(raritiesBox);
  const chosenProfessions = checkedValues(professionsBox);
  const counts = new Map(); const soloCounts = new Map(); let matched = 0;
  const selectedRecords = records.filter(r => r[0] >= min && r[0] <= max && chosenTypes.has(r[1]));
  matched = selectedRecords.length;
  let jobs;
  if (dedupeStage.checked) {{
    const namesByStage = new Map();
    selectedRecords.forEach(r => {{
      if (!namesByStage.has(r[0])) namesByStage.set(r[0], new Set());
      r[2].forEach(name => namesByStage.get(r[0]).add(name));
    }});
    jobs = [...namesByStage.values()];
    jobs.forEach(names => names.forEach(name => counts.set(name, (counts.get(name) || 0) + 1)));
  }} else {{
    selectedRecords.forEach(r => r[2].forEach(name => counts.set(name, (counts.get(name) || 0) + 1)));
    jobs = selectedRecords.map(record => new Set(record[2]));
  }}
  jobs.forEach(names => {{
    const highRarity = [...names].filter(name => operatorMetadata[name] && operatorMetadata[name][1] > 3);
    if (highRarity.length === 1) soloCounts.set(highRarity[0], (soloCounts.get(highRarity[0]) || 0) + 1);
  }});
  const comboCounts = new Map();
  if (bestCombo.checked) jobs.forEach(names => {{
    const eligible = [...names].filter(name => operatorMetadata[name] && operatorMetadata[name][1] >= 3 && matchesOwnership(name));
    for (const name of eligible) for (const partner of eligible) {{
      if (name < partner) {{ const key = name * operatorNames.length + partner; comboCounts.set(key, (comboCounts.get(key) || 0) + 1); }}
    }}
  }});
  const rankingCounts = bestCombo.checked ? new Map() : (onlySolo.checked ? soloCounts : counts);
  let ranked;
  if (bestCombo.checked) {{
    for (const [key, value] of comboCounts) {{
      const name = Math.floor(key / operatorNames.length);
      if (!matchesOperator(name, chosenRarities, chosenProfessions)) continue;
      const current = rankingCounts.get(name);
      if (!current || value > current[1]) rankingCounts.set(name, [key % operatorNames.length, value]);
    }}
    ranked = [...rankingCounts.entries()].map(([name, [partner, value]]) => [name, value, partner]);
  }} else {{
    ranked = [...rankingCounts.entries()]
      .filter(([name]) => matchesOperator(name, chosenRarities, chosenProfessions))
      .map(([name, value]) => [name, value]);
  }}
  ranked.sort((a,b) => b[1] - a[1] || operatorNames[a[0]].localeCompare(operatorNames[b[0]], 'zh-CN'));
  rankingNote.textContent = bestCombo.checked ? '按同时上场次数降序 · 默认显示前 20 位' : (onlySolo.checked ? '按单核次数降序 · 默认显示前 20 位' : '按出现次数降序 · 默认显示前 20 位');
  countLabel.textContent = bestCombo.checked ? '同时上场次数' : (onlySolo.checked ? '单核次数' : '出现次数');
  const maxCount = ranked.length ? Math.max(...ranked.map(item => item[1])) : 0;
  const visible = showAll ? ranked : ranked.slice(0, 20); chart.textContent = '';
  if (!visible.length) {{ const empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = '没有符合筛选条件的干员'; chart.append(empty); }}
  else visible.forEach(([name, value, partner]) => {{
    const row = document.createElement('div'); row.className = 'bar-row';
    const n = document.createElement('div'); n.className = 'name'; n.title = bestCombo.checked ? `${{operatorNames[name]}} + ${{operatorNames[partner]}}` : operatorNames[name];
    const addOperatorLink = operatorId => {{
      const operatorName = operatorNames[operatorId];
      const link = document.createElement('a');
      link.href = 'https://prts.wiki/w/' + encodeURIComponent(operatorName);
      link.textContent = operatorName;
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      n.append(link);
    }};
    addOperatorLink(name);
    if (bestCombo.checked) {{ n.append(document.createTextNode(' + ')); addOperatorLink(partner); }}
    const track = document.createElement('div'); track.className = 'track'; const bar = document.createElement('div'); bar.className = 'bar'; bar.style.width = (value / maxCount * 100) + '%'; track.append(bar);
    const v = document.createElement('div'); v.className = 'value'; v.textContent = value; row.append(n, track, v); chart.append(row);
  }});
  loadAll.hidden = ranked.length <= visible.length;
  loadAll.textContent = `加载全部${{ranked.length}}位`;
  summary.textContent = `符合条件的 JSON：${{matched}} 个；干员种类：${{ranked.length}}；当前显示：${{visible.length}} 位；当前范围：${{min}} - ${{max}}`;
}}
dedupeStage.addEventListener('change', update);
onlySolo.addEventListener('change', () => {{ if (onlySolo.checked) bestCombo.checked = false; showAll = false; update(); }});
bestCombo.addEventListener('change', () => {{ if (bestCombo.checked) onlySolo.checked = false; showAll = false; update(); }});
document.querySelector('[data-range="all"]').addEventListener('click', () => setRange(0, 'all'));
document.querySelector('[data-range="new"]').addEventListener('click', () => setRange(Math.floor(maxDataId / 2), 'new'));
document.querySelector('[data-range="latest"]').addEventListener('click', () => setRange(Math.floor(maxDataId * 3 / 4), 'latest'));
loadAll.addEventListener('click', () => {{ showAll = true; update(); }});
minInput.addEventListener('input', () => {{ showAll = false; document.querySelectorAll('.range-preset').forEach(button => button.classList.remove('is-active')); update(); }});
maxInput.addEventListener('input', () => {{ showAll = false; document.querySelectorAll('.range-preset').forEach(button => button.classList.remove('is-active')); update(); }});
function addOwnerAliases(names) {{
  if (names.has('阿米娅')) {{ names.add('阿米娅(医疗)'); names.add('阿米娅(近卫)'); }}
}}
function syncOwnerUI() {{
  const disabled = !ownedNames;
  ownershipBox.querySelectorAll('input').forEach(input => {{ input.disabled = disabled; }});
  if (disabled) ownershipBox.querySelector('input[value="all"]').checked = true;
  clearOwners.hidden = disabled;
  ownerStatus.classList.remove('is-error');
  ownerStatus.textContent = disabled ? '未上传干员数据，所有权筛选不可用' : `已拥有 ${{ownedCount}} 位干员`;
}}
function currentOwnership() {{
  const checked = ownershipBox.querySelector('input:checked');
  return checked ? checked.value : 'all';
}}
function matchesOwnership(operatorId) {{
  if (!ownedNames) return true;
  const mode = currentOwnership();
  const name = operatorNames[operatorId];
  if (mode === 'owned') return ownedNames.has(name);
  if (mode === 'unowned') return !ownedNames.has(name);
  return true;
}}
function applyOwnerNames(names) {{
  if (!names) {{
    ownedNames = null;
    ownedCount = 0;
    try {{ localStorage.removeItem(OWNER_STORAGE_KEY); }} catch (error) {{ /* 隐私模式下忽略存储异常 */ }}
    ownerFile.value = '';
    syncOwnerUI();
    showAll = false;
    update();
    return;
  }}
  const unique = [...new Set(names)];
  ownedNames = new Set(unique);
  ownedCount = unique.length;
  addOwnerAliases(ownedNames);
  try {{ localStorage.setItem(OWNER_STORAGE_KEY, JSON.stringify({{ v: 1, names: unique }})); }} catch (error) {{ /* 隐私模式下忽略存储异常 */ }}
  syncOwnerUI();
  showAll = false;
  update();
}}
function handleOwnerFile(file) {{
  const reader = new FileReader();
  reader.onerror = () => {{
    ownerStatus.textContent = '读取文件失败，请重试';
    ownerStatus.classList.add('is-error');
  }};
  reader.onload = () => {{
    try {{
      const data = JSON.parse(String(reader.result).trim());
      if (!Array.isArray(data)) throw new Error('顶层不是数组，可能不是 MAA 导出的干员数据');
      if (!data.some(item => item && typeof item.own === 'boolean')) throw new Error('没有找到 own 字段，可能不是 MAA 导出的干员数据');
      const names = [];
      for (const item of data) {{
        if (!item || typeof item !== 'object' || typeof item.name !== 'string' || !item.name.trim()) throw new Error('存在缺少 name 的条目');
        if (item.own === true) names.push(item.name.trim());
      }}
      applyOwnerNames(names);
    }} catch (error) {{
      ownerStatus.textContent = '读取失败：' + error.message;
      ownerStatus.classList.add('is-error');
    }}
  }};
  reader.readAsText(file);
}}
ownershipBox.addEventListener('change', () => {{ showAll = false; update(); }});
pickOwnerFile.addEventListener('click', () => ownerFile.click());
ownerFile.addEventListener('change', () => {{
  const file = ownerFile.files && ownerFile.files[0];
  if (file) handleOwnerFile(file);
}});
clearOwners.addEventListener('click', () => {{ applyOwnerNames(null); }});
try {{
  const savedRaw = localStorage.getItem(OWNER_STORAGE_KEY);
  const saved = savedRaw ? JSON.parse(savedRaw) : null;
  if (saved && saved.v === 1 && Array.isArray(saved.names)) {{
    const names = saved.names.filter(name => typeof name === 'string' && name.trim());
    if (names.length) {{
      ownedNames = new Set(names);
      ownedCount = names.length;
      addOwnerAliases(ownedNames);
    }}
  }}
}} catch (error) {{ /* 本地数据损坏则忽略 */ }}
syncOwnerUI();
setRange(0, 'all');
</script>
</body>
</html>'''
    output.write_text(html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-dir", type=Path, default=script_dir / "作业", help="作业 JSON 目录")
    parser.add_argument("--output-dir", type=Path, default=script_dir / "public", help="HTML 输出目录")
    parser.add_argument("--operators-json", type=Path, default=script_dir / "operators.json", help="干员星级和职业数据 JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.jobs_dir.resolve()
    if not root.is_dir():
        print(f"错误：作业目录不存在：{root}", file=sys.stderr)
        return 2
    files = iter_json_files(root)
    records, skipped = load_html_records(files, root)
    try:
        operator_metadata = load_operator_metadata(args.operators_json)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"错误：无法读取干员数据 {args.operators_json}：{exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "index.html"
    write_html_report(output, records, operator_metadata)
    print(f"扫描 JSON：{len(files)} 个；有效记录：{len(records)} 个；跳过：{len(skipped)} 个；输出：{output}")
    for path, reason in skipped:
        print(f"跳过：{path}（{reason}）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
