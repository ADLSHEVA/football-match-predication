// English translations, keyed by the Chinese source string.
// Missing keys fall back to the Chinese original (see src/i18n.jsx).
export const EN = {
  // ── App shell / nav / titles ─────────────────────────────
  '欧洲足球比赛胜率量化预测系统': 'Football Match Win-Probability Quant System',
  '实时模拟预测': 'Live Simulation',
  '联赛积分战力分布': 'League Standings & Power',
  '2026 世界杯全赛程量化模拟': '2026 World Cup Tournament Simulation',
  'v3.0布莱顿量化版': 'v3.0 Brighton Quant',
  '预测大厅': 'Predictions',
  '战力与积分榜': 'Power & Standings',
  '世界杯 2026': 'World Cup 2026',
  '由 Gemini 3.5 Flash 编写交互前端 · Claude 4.6 Opus 编写预测模型后端':
    'Interactive frontend by Gemini · Prediction models by Claude',
  '切换到英文': 'Switch to English',
  '切换到中文': 'Switch to Chinese',
  '重试': 'Retry',

  // ── Dashboard (Predictions hall) ─────────────────────────
  '系统就绪。点击同步或训练按钮开始。\n': 'System ready. Click Sync or Train to begin.\n',
  '无法连接到 API 后端，请确保 FastAPI 服务器已正常启动。':
    'Cannot reach the API backend — make sure the FastAPI server is running.',
  '开始同步': 'Syncing', '联赛数据...': 'league data...',
  '同步成功！新增比赛/xG数据: ': 'Sync complete. New matches / xG data: ',
  '提示: ': 'Note: ',
  '同步失败: ': 'Sync failed: ',
  '同步出错: ': 'Sync error: ',
  '预测失败': 'Prediction failed',
  '开始基于历史 xG 数据拟合 Dixon-Coles 模型与 ELO...':
    'Fitting the Dixon-Coles model and ELO from historical xG data...',
  '模型训练完成！\n': 'Model training complete!\n',
  '- 拟合球队数量: ': '- Teams fitted: ',
  '- 主场优势因子 (Home Adv): ': '- Home advantage: ',
  '- 低进球相关修正 (Rho): ': '- Low-score correlation (Rho): ',
  '训练失败: ': 'Training failed: ',
  '训练出错: ': 'Training error: ',
  '联赛的 Dixon-Coles 实力估值模型尚未训练！请在右侧控制面板进行「同步」与「训练」。':
    "league's Dixon-Coles strength model isn't trained yet. Use Sync and Train in the control panel on the right.",
  '系统警告: ': 'Warning: ',
  '未配置 Football-Data.org API Key。历史数据将从免费CSV源加载，但无法获取未来赛程。请在项目根目录 .env 文件中设置 FOOTBALL_DATA_API_KEY（免费注册: https://www.football-data.org/）':
    'No Football-Data.org API key configured. Historical data loads from the free CSV source, but upcoming fixtures are unavailable. Set FOOTBALL_DATA_API_KEY in the project-root .env file (free signup: https://www.football-data.org/).',
  '选择目标联赛': 'Select a league',
  '赛程与胜率预测 (Dixon-Coles 基准)': 'Fixtures & Win Probabilities (Dixon-Coles baseline)',
  '展示未来即将进行的比赛。点击「模拟微调」进入星蜥定量面板。':
    'Upcoming matches. Click "Simulate" to open the quant tuning panel.',
  '刷新数据': 'Refresh data', '刷新中...': 'Refreshing...', '刷新': 'Refresh',
  '正在拉取赛事数据...': 'Loading fixtures...',
  '未定': 'TBD', '赔率可用': 'Odds available',
  'Dixon-Coles 胜率:': 'Dixon-Coles win prob:', '均值: ': 'Mean: ',
  'ELO 胜率: ': 'ELO win prob: ', '% 主胜': '% home', '模拟微调': 'Simulate',
  '已获取赛程，但由于实力估值模型未训练，无法显示胜率预测。请在右侧控制面板点击「同步」和「拟合模型」。':
    'Fixtures loaded, but win probabilities need a trained strength model. Click Sync and Fit Model in the control panel.',
  '基准数据未加载': 'Baseline not loaded', '强制模拟': 'Force simulate',
  '欧冠当前无已安排的比赛，或赛季间歇期。': 'No Champions League matches scheduled, or off-season break.',
  '赛季已结束或暂无未来赛程。': 'season has ended or has no upcoming fixtures.',
  '你可以在下方手动选择两支球队进行预测，或切换到其他联赛。':
    'Pick two teams below to predict manually, or switch leagues.',
  '手动选择比赛进行预测': 'Pick a match to predict manually',
  '假想对战预测': 'Hypothetical Match',
  '选择任意两支球队，立即预测假想对战结果（无需有真实赛程）。':
    'Pick any two teams to instantly predict a hypothetical match — no live fixture required.',
  '球队列表为空，请先在右侧「数据同步与模型训练」面板点击同步与拟合。':
    'No teams loaded yet. Use the "Data Sync & Model Training" panel to sync and fit first.',
  '可使用上方的「假想对战预测」面板，或切换其他联赛。':
    'Use the Hypothetical Match panel above, or switch leagues.',
  '选择主队': 'Home team', '选择客队': 'Away team', '预测': 'Predict',
  '期望进球: ': 'Expected goals: ', 'ELO: ': 'ELO: ',
  '进入模拟微调面板': 'Open simulation panel', '重新同步': 'Re-sync',
  '数据同步与模型训练': 'Data Sync & Model Training',
  '当前联赛实力估值模型: ': 'Strength model for this league: ',
  '已训练 (Fitted)': 'Fitted', '未准备 (Not Fitted)': 'Not fitted',
  '正在同步数据...': 'Syncing data...', '1. 同步英超/西甲数据': '1. Sync league data',
  '正在训练拟合中...': 'Fitting...', '2. 拟合 Dixon-Coles 模型': '2. Fit Dixon-Coles model',
  '系统实时运行日志:': 'Live system log:',
  '布莱顿量化回测效果': 'Quant Backtest Performance',
  '模型回测预测总数:': 'Total backtested predictions:', ' 场': '',
  '主平客准确预测:': 'Correct (1X2) predictions:',
  '总体基准胜率 (Hit Rate):': 'Overall hit rate:',
  '* 注: 对于三项胜率预测(主胜/平局/客胜)，命中率高于 52% 即可跑赢庄家，55% 以上属于专业基金量化水平。':
    '* Note: for 1X2 predictions, a hit rate above 52% beats the bookmaker; above 55% is professional quant-fund level.',

  // ── World Cup: page shell ────────────────────────────────
  '实时数据': 'Live data',
  '实时结果 + 种子实力': 'Live results + seeded strengths',
  '内置种子数据': 'Built-in seed data',
  '服务器错误 (HTTP ': 'Server error (HTTP ',
  '无法连接到后端 API。': 'Cannot reach the backend API.',
  '2026 世界杯 · 全赛程量化模拟': '2026 World Cup · Full-Tournament Simulation',
  '48 强 / 12 组 · 基于 Elo 实力先验的蒙特卡洛全赛事推演（小组赛 → 淘汰赛 → 夺冠）。':
    '48 teams / 12 groups · Elo-seeded Monte-Carlo of the whole tournament (groups → knockout → champion).',
  '次模拟': 'sims',
  '刷新实时数据并重新模拟': 'Refresh live data and re-simulate',
  '模拟中...': 'Simulating...',
  '数据源: ': 'Source: ',
  '已录入赛果: ': 'Results in: ',
  '模拟次数: ': 'Simulations: ',
  '当前使用内置 2026 种子数据（分组为示意，非官方抽签）。配置 FOOTBALL_DATA_API_KEY 后点击「刷新」即可接入真实赛程与赛果。':
    'Showing built-in 2026 seed data (illustrative groups, not the official draw). Configure FOOTBALL_DATA_API_KEY and click Refresh to pull the real schedule and results.',
  '夺冠概率': 'Title Odds',
  '小组赛': 'Groups',
  '淘汰赛对阵': 'Bracket',
  '实时赛况': 'Live',
  '正在推演': 'Simulating',
  '届世界杯...': 'World Cups...',

  // ── World Cup: schedule / results ────────────────────────
  '32 强': 'Round of 32', '16 强': 'Round of 16', '1/4 决赛': 'Quarter-finals',
  '半决赛': 'Semi-finals', '季军赛': 'Third place', '决赛': 'Final',
  '主胜': 'Home', '平局': 'Draw', '客胜': 'Away',
  '正在加载真实赛程与赛果...': 'Loading real schedule and results...',
  '加载赛程失败: ': 'Failed to load schedule: ',
  '未获取到实时赛程（检查 FOOTBALL_DATA_API_KEY）。当前展示内置数据，无真实赛果与开赛时间。':
    'No live schedule (check FOOTBALL_DATA_API_KEY). Showing built-in data without real results or kick-off times.',
  '模型预测准确度 (随真实赛果自我校准)': 'Model accuracy (self-calibrating from real results)',
  '胜平负命中 (': '1X2 hits (', '精确比分命中 (': 'Exact-score hits (',
  'Brier 分 (越低越准)': 'Brier score (lower is better)',
  '已校准场均进球': 'Calibrated goals/team', '实测场均进球/队': 'Observed goals/team',
  '每场赛前用「截至该场之前」的实力做预测并锁定；赛后与真实比分对比。Elo 随每场结果更新，进球模型按实测比分收缩校准——这就是「基于实际结果改进预测」。':
    'Each match is predicted (and locked) from strengths as of just before kick-off, then compared with the real score. Elo updates after every result and the goal model shrinks toward observed scores — that is how predictions improve from real results.',
  '即将开赛 · 赛前预测 (': 'Upcoming · pre-match predictions (',
  '开赛时间为中欧夏令时 (CEST, UTC+2)。颜色条为主胜/平/客胜概率。':
    'Kick-off in Central European Summer Time (CEST, UTC+2). Bars show home/draw/away probability.',
  '已结束 · 预测 vs 实际 (': 'Finished · predicted vs actual (',
  '胜平负命中': '1X2 hit', '精确比分命中': 'exact-score hit',
  '暂无已结束的比赛。': 'No finished matches yet.',
  '显示全部': 'Show all', '收起': 'Collapse',
  '预测 ': 'Predicted ', '● 进行中': '● Live', '赛前预测': 'Pre-match prediction',

  // ── World Cup: title odds / groups / bracket ─────────────
  '夺冠概率排行 (蒙特卡洛全赛程模拟)': 'Championship odds (full-tournament Monte-Carlo)',
  '决赛 ': 'Final ', ' · 4强 ': ' · SF ', ' 支球队': ' teams',
  '直接出线 (前二)': 'Auto-qualify (top 2)', '小组第三 (争最佳8席)': '3rd place (best-8 race)',
  '小组 ': 'Group ', '球队': 'Team', '均分': 'Pts', '出线率': 'Adv%',
  '淘汰赛对阵预测 (模型最可能晋级路径)': 'Projected bracket (model\'s most-likely path)',
  '小组名次按模拟均分排定，淘汰赛每场高亮一方为模型favorite——仅为最可能路径，非确定结果。':
    'Group ranks are by mean simulated points; in each knockout tie the model favourite is highlighted — a most-likely path, not a certain outcome.',
  '冠军': 'Champion', '% 夺冠': '% title',

  // ── Common team words ────────────────────────────────────
  '主队': 'Home', '客队': 'Away', '主': 'Home', '客': 'Away',
  '胜': 'win', '胜率': 'win %', '球': 'goals',

  // ── League selector ──────────────────────────────────────
  '英超 (Premier League)': 'Premier League',
  '西甲 (La Liga)': 'La Liga',
  '德甲 (Bundesliga)': 'Bundesliga',
  '意甲 (Serie A)': 'Serie A',
  '法甲 (Ligue 1)': 'Ligue 1',
  '欧冠 (Champions League)': 'Champions League',
  '🏴󠁧󠁢󠁥󠁮󠁧󠁿 英格兰': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 England',
  '🇪🇸 西班牙': '🇪🇸 Spain',
  '🇩🇪 德国': '🇩🇪 Germany',
  '🇮🇹 意大利': '🇮🇹 Italy',
  '🇫🇷 法国': '🇫🇷 France',
  '🇪🇺 欧洲': '🇪🇺 Europe',

  // ── DynamicSliders ───────────────────────────────────────
  '临场状态': 'match-day form',
  '进攻系数 (Attack Modifier)': 'Attack Modifier',
  '防守系数 (Defense Modifier)': 'Defense Modifier',
  '体能衰减 (Stamina Decay)': 'Stamina Decay',
  '1.0=基准 | 0.8=主力缺阵 | 1.2=状态爆棚': '1.0=base | 0.8=key player out | 1.2=in top form',
  '1.0=基准 | 1.2=漏斗防线 | 0.8=防守铜墙铁壁': '1.0=base | 1.2=leaky defense | 0.8=rock solid',
  '后半场疲劳度。0=正常 | 0.15=双线作战/体能危机': 'Late-game fatigue. 0=normal | 0.15=fixture congestion',
  '比赛全局战术': 'Match-wide Tactics',
  '战术保守度 (Tempo / Openness)': 'Tactical Conservatism (Tempo / Openness)',
  '两队进球倾向。0.7=沉闷防守大战 | 1.3=对攻大球局': "Both teams' scoring tempo. 0.7=cagey | 1.3=open & high-scoring",
  '领先队死守战术 (Park the Bus)': 'Park the Bus (leader defends)',
  '领先一球后是否收缩防守': 'Whether the leader sits back after going 1-0 up',
  '死守触发时间 (Trigger Minute)': 'Trigger minute',
  '第 ': 'Min ', ' 分钟': '',

  // ── MatchSimulator ───────────────────────────────────────
  '模拟失败，后端返回错误': 'Simulation failed — backend returned an error',
  '返回赛程控制台 (Dashboard)': 'Back to Dashboard',
  'xG 期望: ': 'xG expected: ', '基准 xG: ': 'Baseline xG: ',
  '模拟出错: ': 'Simulation error: ',
  '。请确保模型已拟合，或者返回主页重试。': '. Make sure the model is fitted, or go back and retry.',
  '星蜥定量微调层': 'Starlizard Quant Tuning',
  '重置': 'Reset',
  '蒙特卡洛仿真输出 (基于 10,000 次时间步迭代)': 'Monte-Carlo Output (10,000 time-step iterations)',
  '平局概率': 'Draw %',
  '最可能出现的精确比分 (Top 5)': 'Most Likely Exact Scores (Top 5)',
  '进球数大小盘口概率 (Over/Under)': 'Over/Under Goal-Line Probabilities',
  '进球盘口': 'Line', '大球概率 (Over)': 'Over', '小球概率 (Under)': 'Under',
  '正在计算蒙特卡洛赔率...': 'Computing Monte-Carlo odds...',

  // ── Standings ────────────────────────────────────────────
  '无法获取积分榜数据，可能是 API Key 达到限制或网络问题': 'Failed to load standings — API key limit reached or a network issue.',
  '选择目标联赛积分榜': 'Select a league table',
  '当前积分与量化指标对比': 'Standings vs Quant Metrics',
  '结合实时联赛积分，与 Dixon-Coles 拟合进攻/防守实力 (α, β) 和当前 ELO。':
    'Live league points alongside Dixon-Coles attack/defense strengths (α, β) and current ELO.',
  '错误: ': 'Error: ',
  '正在载入联赛数据与拟合指标...': 'Loading league data and fitted metrics...',
  '排名': 'Rank', '已赛': 'P', '胜/平/负': 'W/D/L', '进/失/净': 'GF/GA/GD',
  '积分': 'Pts', 'ELO 评分': 'ELO', '进攻强度 (α)': 'Attack (α)', '防守强度 (β)': 'Defense (β)',
  '未拟合': 'not fitted',
  '暂无当前联赛积分榜数据，请检查网络或在主页同步数据。':
    'No standings for this league. Check your connection or sync data on the home page.',

  // ── OddsPanel ────────────────────────────────────────────
  '赔率对比与价值投注': 'Odds & Value Bets',
  '未配置 THE_ODDS_API_KEY，请在 .env 文件中设置。': 'THE_ODDS_API_KEY not configured. Set it in the .env file.',
  '正在获取赔率数据...': 'Loading odds...',
  '暂无该比赛的赔率数据。': 'No odds for this match.',
  '赔率对比与价值投注分析': 'Odds & Value-Bet Analysis',
  '展开': 'Expand',
  '博彩公司': 'Bookmaker',
  '价值投注机会 (EV > 0)': 'Value Bets (EV > 0)',
  '赔率: ': 'Odds: ', '模型: ': 'Model: ',
  '当前赔率与模型估值一致，暂无明显价值投注机会。': 'Odds match the model — no clear value bets right now.',

  // ── H2HPanel ─────────────────────────────────────────────
  '历史交锋记录 (H2H)': 'Head-to-Head (H2H)',
  '未配置 API_FOOTBALL_KEY，请在 .env 文件中设置。': 'API_FOOTBALL_KEY not configured. Set it in the .env file.',
  '正在查询历史交锋...': 'Loading head-to-head...',
  '暂无历史交锋数据。': 'No head-to-head data.',
  '历史交锋记录 (近 ': 'Head-to-Head (last ', ' 场)': ')',
  '场均进球: ': 'Avg goals: ',
  '日期': 'Date', '比分': 'Score',

  // ── LineupPanel ──────────────────────────────────────────
  '阵容与阵型分析': 'Lineups & Formation Analysis',
  '正在查询阵容信息...': 'Loading lineups...',
  '阵容尚未公布（通常在比赛前1小时左右确认）': 'Lineups not announced yet (usually confirmed ~1h before kick-off).',
  '首发阵容': 'Starting XI',
  '球员': 'Player', '位置': 'Pos', '主教练: ': 'Coach: ',

  // ── ScoreMatrix ──────────────────────────────────────────
  '比分概率分布图 (Heatmap)': 'Score Probability Heatmap',
  '将鼠标悬停在单元格上以查看详细概率': 'Hover a cell to see the exact probability',

  // ── PredictionGauge (title tooltips) ─────────────────────
  '主队胜率: ': 'Home win: ', '平局概率: ': 'Draw: ', '客队胜率: ': 'Away win: ',
};
