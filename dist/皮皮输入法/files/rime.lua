-- 皮皮输入法 · 阶段 4
-- 这一版做的三件事：
--   1. 空格/回车改成「确认键」：像拼音就上屏中文候选，像英文就把字母原样打出去
--   2. 英文单词不再弹中文候选（候选栏只留一个原文候选）
--   3. 保留前面的修复：按下/松开不重复、退格不删正文、数字选候选
--
-- 注意：librime-lua 里有的成员是属性、有的是方法，统一用 prop() 取，避免踩坑

local function prop(obj, name)
  local v = obj[name]
  if type(v) == "function" then
    return v(obj)
  end
  return v
end

-- 前向声明：这两个函数定义在文件末尾，但处理器里要用
local write_state, apply_command

-- ============================================================
-- 一、合法拼音音节表
-- 用途：判断一串字母能不能被完整切成拼音，切不开就说明是英文
-- ============================================================
local PINYIN = {}
for s in ([[
a ai an ang ao
ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu
ca cai can cang cao ce cen ceng cha chai chan chang chao che chen cheng
chi chong chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu
cuan cui cun cuo
da dai dan dang dao de dei den deng di dia dian diao die ding diu dong
dou du duan dui dun duo
e ei en eng er
fa fan fang fei fen feng fo fou fu
ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui
gun guo
ha hai han hang hao he hei hen heng hong hou hu hua huai huan huang hui
hun huo
ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun
ka kai kan kang kao ke ken keng kong kou ku kua kuai kuan kuang kui kun kuo
la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu
long lou lu luan lun luo lv lve
ma mai man mang mao me mei men meng mi mian miao mie min ming miu mo mou mu
na nai nan nang nao ne nei nen neng ni nian niang niao nie nin ning niu
nong nou nu nuan nuo nv nve
ou
pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu
qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun
ran rang rao re ren reng ri rong rou ru rua ruan rui run ruo
sa sai san sang sao se sen seng sha shai shan shang shao she shei shen
sheng shi shou shu shua shuai shuan shuang shui shun shuo si song sou su
suan sui sun suo
ta tai tan tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun
tuo
wa wai wan wang wei wen weng wo wu
xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun
ya yan yang yao ye yi yin ying yo yong you yu yuan yue yun
za zai zan zang zao ze zei zen zeng zha zhai zhan zhang zhao zhe zhen
zheng zhi zhong zhou zhu zhua zhuai zhuan zhuang zhui zhun zhuo zi zong
zou zu zuan zui zun zuo
]]):gmatch("%S+") do
  PINYIN[s] = true
end

-- ============================================================
-- 二、常见英文词表
-- 有些词恰好能切成合法拼音（meeting = me e ting），靠这张表兜底
-- 现在已经写的词判断优先级高于拼音切分，所以不必收录全部，覆盖高频即可
-- ============================================================
local ENGLISH = {}
for w in ([[
the be to of and in that have it for not on with he as you do at this
but his by from they we say her she or an will my one all would there their
what so up out if about who get which go me when make can like time no just
him know take people into year your good some could them see other than then
now look only come its over think also back after use two how our work first
well way even new want because any these give day most us is are was were
been has had did does
hello hi hey ok okay yes yeah nope thanks thank please sorry excuse bye
goodbye morning evening night welcome cheers regards best wish dear sir madam
meeting meetings call video chat email mail inbox reply forward attach
attachment file files folder document doc docs sheet report slides deadline
schedule calendar agenda minute minutes project task tasks team teams group
office company client customer user users account manager boss leader
colleague partner vendor supplier contract order invoice price prices cost
budget payment paid refund bill quote discount total product service support
help question questions answer problem issue bug error fix update upgrade
version release deploy server client network data database table query
script code feature test tests testing debug build commit push pull merge
branch repo repository git frontend backend fullstack api url http https
request response json xml login logout signin signup password username admin
root config settings install download upload delete remove create edit save
open close start stop run running done finish finished begin today tomorrow
yesterday week month year monday tuesday wednesday thursday friday saturday
sunday january february march april may june july august september october
november december afternoon date hour second later soon before during between
until since always never often sometimes usually rarely again already still
yet very really quite too much many few little lot more less most least big
small large long short high low wide narrow thick thin new old young fresh
recent current latest modern classic bad great nice fine poor excellent
perfect worse better best worst happy sad angry tired busy free easy hard
difficult simple complex important urgent normal special general public
private local global fast quick slow late early ready buy sell pay spend earn
lose win keep hold give take send receive deliver ship return read write speak
talk listen hear watch find search understand learn teach remember forget
explain show tell ask agree disagree accept refuse allow deny play rest sleep
eat drink walk drive fly travel stay live meet visit join leave arrive move
turn follow lead lock unlock click drag drop copy paste cut print scan type
press touch scroll zoom phone mobile laptop desktop screen keyboard mouse
monitor printer windows mac linux android ios app software hardware system
internet wifi profile link site page website homepage browser tab window
button icon menu message note news post comment share subscribe money cash
card bank fee tax name age address city country street road number man woman
boy girl child person friend family food water tea coffee milk rice bread
meat fish fruit vegetable red green blue black white yellow gray brown pink
purple orange three four five six seven eight nine ten third next previous
final here where everywhere somewhere nowhere anywhere those
]]):gmatch("%S+") do
  ENGLISH[w] = true
end

-- ============================================================
-- 三、判断这一串字母是拼音还是英文
-- ============================================================

-- 能否被完整切成合法拼音音节（从左往右取最长匹配）
local function can_split(s)
  local i, n, count = 1, #s, 0
  while i <= n do
    local matched = false
    local maxlen = math.min(6, n - i + 1)
    for len = maxlen, 1, -1 do
      if PINYIN[s:sub(i, i + len - 1)] then
        i = i + len
        count = count + 1
        matched = true
        break
      end
    end
    if not matched then
      return false, 0
    end
  end
  return true, count
end

local function looks_english(s)
  if s == nil or s == "" then
    return false
  end
  local low = s:lower()
  -- 一两个字母：是拼音音节就当拼音（w、wo、a），否则当英文（ok、hi）
  if #low <= 2 then
    return not PINYIN[low]
  end
  if ENGLISH[low] then
    return true
  end
  if not can_split(low) then
    return true
  end
  return false
end

-- ============================================================
-- 四、按键处理器
-- ============================================================
local function is_letter(kc)
  return (kc >= 97 and kc <= 122) or (kc >= 65 and kc <= 90)
end

local function is_digit(kc)
  return kc >= 0x31 and kc <= 0x39
end

local function is_pipi_key(kc)
  return is_letter(kc) or is_digit(kc)
      or kc == 0x20 or kc == 0xff08 or kc == 0xff0d or kc == 0xff1b
end

function pipi_ascii(key, env)
  local ctx = env.engine.context

  -- 先执行状态栏发来的命令，再把当前状态写回去
  apply_command(ctx)
  write_state(ctx)

  local ascii_mode = ctx:get_option("ascii_mode")

  local kc = key.keycode
  if not is_pipi_key(kc) then
    return 2
  end

  -- 松开事件直接吃掉。小狼毫会为每个按键补发一次松开，不判断就会重复输入
  if prop(key, "release") then
    return 1
  end

  -- 空格 / 回车：确认键，两种模式下行为一致
  -- 这是「不用切模式」的关键：像英文就出英文，像拼音就上屏中文
  if kc == 0x20 or kc == 0xff0d then
    if not ctx:is_composing() then
      return 2
    end
    local input = prop(ctx, "input") or ""
    if looks_english(input) then
      local suffix = (kc == 0x20) and " " or ""
      env.engine:commit_text(input .. suffix)
      ctx:clear()
      return 1
    end
    -- 像拼音：中文模式下交给 Rime 原生逻辑上屏第一候选；
    -- 英文模式下 Rime 原生会把原文打出去，所以这里必须自己选候选
    if ascii_mode then
      if ctx:has_menu() then
        ctx:select(0)
      else
        env.engine:commit_text(input)
        ctx:clear()
      end
      return 1
    end
    return 2
  end

  -- 以下只处理英文（西文）模式。
  -- 中文模式下字母、数字、退格本来就走 Rime 原生逻辑，不插手最稳。
  if not ascii_mode then
    return 2
  end

  -- 退格：只删输入框里的字母
  if kc == 0xff08 then
    if ctx:is_composing() then
      ctx:pop_input(1)
      return 1
    end
    return 2
  end

  -- Esc：放弃这次输入
  if kc == 0xff1b then
    if ctx:is_composing() then
      ctx:clear()
      return 1
    end
    return 2
  end

  -- 数字 1-9：有输入时选候选
  if is_digit(kc) then
    if ctx:is_composing() then
      ctx:select(kc - 0x31)
      return 1
    end
    return 2
  end

  -- 字母：推进输入缓冲
  ctx:push_input(string.char(kc))
  return 1
end

-- ============================================================
-- 五、候选过滤器
-- ============================================================
-- 目标形态（竖排，一行一个候选）：
--   像拼音   →  1. 我要吃饭        ← 自动识别出来的主候选永远第一个
--               2. woyaochifan     ← 想让字母原样上屏（输网址、写变量名）按 2
--               3. 我要吃
--               4. 我要
--   像英文   →  1. meeting         ← 英文原文第一，空格直接上屏
--               2. 么额听          ← 中文作为备选跟在后面
--
-- 说明：右侧不再显示拼音注释列。那个注释只是装饰，不能单独选中，
-- 反而把候选窗撑宽了；「原样拼音」改成独立候选放在第 2 位才有用。

local function get_input(ctx)
  return prop(ctx, "input") or ""
end

-- ------------------------------------------------------------
-- 标点专用判断
--
-- 为什么单独拎出来：filter 对所有输入都会跑一遍，而标点不在拼音表里，
-- 会被 looks_english 判成「英文」——于是半角原字符被插到候选第一位。
-- 表现就是：中文模式下打逗号，第一候选是「,」，中文的「，」被挤到第二位。
-- 所以标点必须在中英判断之前拦下来，走自己的分支。
-- ------------------------------------------------------------

-- 纯符号输入（只含 ASCII 标点/空白，不含字母数字）
local function is_symbol(s)
  return s ~= "" and #s <= 4 and s:match("^[%p%s]+$") ~= nil
end

-- 上一段上屏文字是不是英文
-- 取结尾那段连续字母来判断：中文后面跟字母才算英文，
-- 以中文结尾的一律按中文语境处理
local function prev_is_english(ctx)
  local h = prop(ctx, "commit_history")
  if h == nil then
    return false
  end
  local rec = prop(h, "back")
  if rec == nil then
    return false
  end
  local word = (rec.text or ""):match("([%a]+)%s*$")
  if word == nil or #word < 2 then
    return false
  end
  return looks_english(word)
end

function pipi_filter(input, env)
  local ctx = env.engine.context
  write_state(ctx)
  -- 注意：filter 拿到的 translation 对象不暴露输入串，要从上下文取
  local s = get_input(ctx)
  if s == "" then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  -- ① 标点：不进中英判断，只看上一段上屏的是中文还是英文
  if is_symbol(s) then
    if prev_is_english(ctx) then
      -- 刚打完英文 → 半角符号直接上屏，中文标点不再出现
      yield(Candidate("pipi_punct", 0, #s, s, ""))
      return
    end
    -- 中文语境 → 原样放行。Rime 对常用标点只给一个中文候选，
    -- 单候选会自动上屏，所以连候选窗都不会弹出来
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  -- ② 像英文：原文就是第一候选（空格上屏它），中文跟在后面当备选
  if looks_english(s) then
    yield(Candidate("pipi_raw", 0, #s, s, ""))
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  -- ③ 像拼音：中文原序不动，但「原样拼音」固定插在第 2 位
  local fallback = nil
  if #s >= 1 and #s <= 30 then
    fallback = Candidate("pipi_pinyin", 0, #s, s, "")
  end

  local n, placed = 0, false
  for cand in input:iter() do
    yield(cand)
    n = n + 1
    if fallback and n == 1 then
      yield(fallback)
      placed = true
    end
  end
  -- 兜底：拼音一个候选都没翻译出来时，至少留个能上屏原文的
  if fallback and not placed then
    yield(fallback)
  end
end

-- ============================================================
-- 六、翻译器（暂空，保留挂载点）
-- ============================================================
function pipi_test(input, seg, env)
  return
end

-- ============================================================
-- 七、状态栏通信
-- ============================================================
-- 状态栏是独立进程，拿不到输入法的内存，所以用文件当信道：
--   输入法 → 状态栏：写 pipi-state.json（状态栏每 250ms 看一眼）
--   状态栏 → 输入法：写 pipi-cmd.json（按键时读取并执行后删除）
-- 这个做法很土，但不用做 IPC，出问题也查得清楚。

local STATE_NAME = "\\Rime\\pipi-state.json"
local CMD_NAME = "\\Rime\\pipi-cmd.json"
local last_state_sig = ""

local function user_path(name)
  local appdata = os.getenv("APPDATA")
  if not appdata then
    return nil
  end
  return appdata .. name
end

function write_state(ctx)
  local path = user_path(STATE_NAME)
  if not path then
    return
  end
  local punct = ctx:get_option("ascii_punct") and "en" or "cn"
  local variant = ctx:get_option("zh_simp") and "simp" or "trad"
  local sig = punct .. "|" .. variant
  if sig == last_state_sig then
    return
  end
  last_state_sig = sig
  local f = io.open(path, "w")
  if not f then
    return
  end
  f:write(string.format('{"punct":"%s","variant":"%s"}', punct, variant))
  f:close()
end

function apply_command(ctx)
  local path = user_path(CMD_NAME)
  if not path then
    return
  end
  local f = io.open(path, "r")
  if not f then
    return
  end
  local body = f:read("*a")
  f:close()
  os.remove(path)
  local cmd = body:match('"cmd"%s*:%s*"([^"]+)"')
  if cmd == "punct" then
    ctx:set_option("ascii_punct", not ctx:get_option("ascii_punct"))
  elseif cmd == "variant" then
    ctx:set_option("zh_simp", not ctx:get_option("zh_simp"))
  end
  last_state_sig = ""  -- 强制下次写一次，让状态栏立刻更新
end
