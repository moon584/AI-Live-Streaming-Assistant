let currentSessionId = null;
let sessionInfo = null;
// 在创建会话时记录一次包含类型的商品快照（用于后续根据类型定制快捷键话术）
let createdProductsSnapshot = [];
let sidebarCollapsed = false;

// API基础URL
// 相对路径方便通过内网穿透或反向代理访问
const API_BASE = '';

// 商品类型属性配置
const productTypeConfig = {
    fruit: {
        name: "水果",
        attributes: [
            { key: "variety", label: "品种", type: "text", placeholder: "例如：红富士/烟台富士" },
            { key: "maturity", label: "成熟度", type: "select", options: ["未熟", "待熟", "适中", "完全熟"] },
            { key: "sweetness", label: "甜度", type: "select", options: ["偏酸", "微甜", "适中", "很甜", "特别甜"] },
            { key: "texture", label: "口感", type: "select", options: ["脆爽", "软糯", "多汁", "绵密", "清脆"] },
            { key: "origin", label: "产地", type: "text", placeholder: "例如：山东烟台" },
            { key: "size", label: "大小规格", type: "text", placeholder: "例如：单果200-250g" },
            { key: "grade", label: "等级", type: "text", placeholder: "例如：一级/二级" },
            { key: "harvest_date", label: "采摘日期", type: "text", placeholder: "例如：2025-09-12" },
            { key: "storage", label: "储存建议", type: "textarea", placeholder: "冷藏保存，建议3天内食用" }
        ]
    },
    vegetable: {
        name: "蔬菜",
        attributes: [
            { key: "variety", label: "品种", type: "text", placeholder: "例如：小青菜/大白菜" },
            { key: "freshness", label: "新鲜度", type: "select", options: ["当日采摘", "隔日送达", "冷链保鲜"] },
            { key: "maturity", label: "成熟度/嫩度", type: "select", options: ["幼嫩", "适中", "成熟"] },
            { key: "cooking", label: "推荐烹饪方式", type: "select", options: ["清炒", "炖煮", "凉拌", "蒸制", "煲汤"] },
            { key: "origin", label: "产地", type: "text", placeholder: "例如：本地大棚" },
            { key: "season", label: "时令季节", type: "text", placeholder: "例如：春季" },
            { key: "storage", label: "储存建议", type: "textarea", placeholder: "冷藏保存，建议尽快食用" }
        ]
    },
    meat: {
        name: "禽蛋肉类",
        attributes: [
            { key: "raising", label: "饲养方式", type: "select", options: ["散养", "圈养", "有机养殖", "放养"] },
            { key: "part", label: "部位", type: "text", placeholder: "例如：鸡胸肉、猪里脊" },
            { key: "quality", label: "肉质/等级", type: "text", placeholder: "例如：鲜嫩/紧实" },
            { key: "slaughter_date", label: "宰杀/处理日期", type: "text", placeholder: "例如：2025-10-01" },
            { key: "origin", label: "来源地", type: "text", placeholder: "例如：山东某养殖场" },
            { key: "storage", label: "储存建议", type: "textarea", placeholder: "冷冻保存，解冻后请尽快食用" }
        ]
    },
    grain: {
        name: "五谷杂粮",
        attributes: [
            { key: "variety", label: "品种", type: "text", placeholder: "例如：东北大米/胚芽米" },
            { key: "origin", label: "产地", type: "text", placeholder: "例如：黑龙江" },
            { key: "moisture", label: "水分含量", type: "text", placeholder: "例如：12%" },
            { key: "processing", label: "加工方式", type: "select", options: ["精加工", "粗加工", "保留胚芽", "无添加"] },
            { key: "cooking", label: "食用/烹煮建议", type: "textarea", placeholder: "浸泡时间/水米比等" },
            { key: "storage", label: "储存建议", type: "textarea", placeholder: "阴凉干燥处保存" }
        ]
    },
    handicraft: {
        name: "手工艺品",
        attributes: [
            { key: "material", label: "材质", type: "text", placeholder: "例如：竹编、陶瓷、布料" },
            { key: "craft", label: "工艺", type: "text", placeholder: "例如：手工编织/传统烧制" },
            { key: "origin", label: "产地/产区", type: "text", placeholder: "例如：江苏苏州" },
            { key: "purpose", label: "用途", type: "select", options: ["装饰", "实用", "收藏", "礼品"] },
            // 手工艺品尺寸使用结构化的长x宽x高（便于前端选择单位与数值）
            { key: "size", label: "尺寸（长×宽×高）", type: "dimensions", subtype: "lwh" },
            { key: "care", label: "保养建议", type: "textarea", placeholder: "避免潮湿/避免阳光直射" },
            { key: "making_time", label: "制作时长", type: "text", placeholder: "例如：3天" }
        ]
    },
    processed: {
        name: "加工食品",
        attributes: [
            { key: "ingredients", label: "主要原料", type: "textarea", placeholder: "列出主要原料" },
            { key: "allergens", label: "过敏原", type: "text", placeholder: "例如：含坚果/含麸质" },
            { key: "shelf_life", label: "保质期", type: "text", placeholder: "例如：6个月" },
            { key: "flavor", label: "风味", type: "select", options: ["甜", "咸", "辣", "酸", "鲜", "原味"] },
            { key: "usage", label: "食用/加热建议", type: "textarea", placeholder: "开袋即食或加热食用" },
            { key: "manufacturer", label: "生产商/厂家", type: "text", placeholder: "例如：某某食品有限公司" },
            { key: "storage", label: "储存建议", type: "textarea", placeholder: "阴凉干燥处保存" }
        ]
    }
};

// NOTE: 原先有一个用于补充信息的 modal（need_info），为简化 UX 已移除，后端若请求补充信息
// 前端将提示用户在左侧的商品表单中补充对应字段后重试。


// 更新商品属性输入区域
function updateProductAttributes(selectElement) {
    const productItem = selectElement.closest('.product-item');
    const attributesContainer = productItem.querySelector('.product-attributes');
    const productType = selectElement.value;
    
    if (productType && productTypeConfig[productType]) {
        const config = productTypeConfig[productType];
        attributesContainer.style.display = 'block';
        attributesContainer.innerHTML = `
            <h4>${config.name} - 商品属性</h4>
            ${config.attributes.map(attr => `
                <div class="attribute-group">
                    <label>${attr.label}</label>
                    ${generateAttributeInput(attr)}
                </div>
            `).join('')}
        `;
        // 为渲染出的属性控件添加自动保存监听：用户修改后自动发送到后端
        try {
            const productNameInput = productItem.querySelector('.product-name');
            const productName = productNameInput ? productNameInput.value.trim() : '';
            const inputs = attributesContainer.querySelectorAll('input[data-key], textarea[data-key], select[data-key]');
            inputs.forEach(inp => {
                const ev = (inp.tagName.toLowerCase() === 'select') ? 'change' : 'blur';
                inp.addEventListener(ev, async (e) => {
                    if (!currentSessionId) return; // 未创建会话则不保存
                    const key = inp.getAttribute('data-key');
                    const subkey = inp.getAttribute('data-subkey');
                    let val = (inp.value || '').toString().trim();
                    if (!key) return;
                    // 对于子字段（data-subkey），我们直接上传子值，服务端应负责合并
                    const sendKey = key;
                    const sendVal = val;
                    if (!productName) return; // 无法识别商品名则跳过
                    // 防抖/节流简单策略：仅在有实际值时发送（若清空则也发送空以表示清除）
                    await saveProductInfoToServer(currentSessionId, productName, sendKey, sendVal);
                });
            });
        } catch (e) {
            // 静默处理，不影响渲染
            console.warn('绑定属性自动保存失败', e);
        }
    } else {
        attributesContainer.style.display = 'none';
        attributesContainer.innerHTML = '';
    }
}

// 生成属性输入框
function generateAttributeInput(attr) {
    // 优化输入控件：尽量使用下拉与结构化输入，减少自由文本
    // 对某些常见字段使用专用控件（例如尺寸 size -> number + unit，采摘/宰杀日期 -> date）
    const key = attr.key;
    if (attr.type === 'select') {
        return `
            <select class="attribute-select" data-key="${key}">
                <option value="">请选择</option>
                ${attr.options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
            </select>
        `;
    }

    // 长×宽×高尺寸：改为单一紧凑文本输入，避免复杂结构在不同浏览器/布局下显示错位
    if (attr.type === 'dimensions' && attr.subtype === 'lwh') {
        return `
            <input type="text" class="attribute-input" data-key="${key}" placeholder="请输入长宽高,例如:20×15×5cm" />
        `;
    }

    if (key === 'harvest_date' || key === 'slaughter_date') {
        return `
            <input type="date" class="attribute-date" data-key="${key}" />
        `;
    }

    if (attr.type === 'textarea') {
        return `
            <textarea class="attribute-textarea" data-key="${key}" placeholder="${attr.placeholder || ''}"></textarea>
        `;
    }

    // 默认：如果提供了 options 用 select，否则用文本输入（但使用 data-key 与可选的 data-subkey 保持兼容）
    if (attr.type === 'text' || !attr.type) {
        return `
            <input type="text" class="attribute-input" data-key="${key}" placeholder="${attr.placeholder || ''}" />
        `;
    }

    // 兜底
    return `
        <input type="text" class="attribute-input" data-key="${key}" placeholder="${attr.placeholder || ''}" />
    `;
}

// 添加商品输入框
function addProduct() {
    const container = document.getElementById('productsContainer');
    const productItem = document.createElement('div');
    productItem.className = 'product-item';
    productItem.innerHTML = `
        <div class="product-basic-info">
            <span class="product-index">#</span>
            <input type="text" class="product-name" placeholder="商品名称" />
            <select class="product-type" onchange="updateProductAttributes(this)">
                <option value="">选择商品类型</option>
                <option value="fruit">水果</option>
                <option value="vegetable">蔬菜</option>
                <option value="meat">禽蛋肉类</option>
                <option value="grain">五谷杂粮</option>
                <option value="handicraft">手工艺品</option>
                <option value="processed">加工食品</option>
            </select>
            <div class="price-unit-group">
                <input type="number" class="product-price price-input" placeholder="价格" step="0.01" min="0" />
                <select class="unit-select">
                    <option value="元/斤">元/斤</option>
                    <option value="元/个">元/个</option>
                    <option value="元/箱">元/箱</option>
                    <option value="元/盒">元/盒</option>
                    <option value="元/袋">元/袋</option>
                    <option value="元/公斤">元/公斤</option>
                    <option value="元/份">元/份</option>
                    <option value="元">元</option>
                </select>
            </div>
            <button class="btn btn-remove" onclick="removeProduct(this)">删除</button>
        </div>
        <div class="product-attributes" style="display: none;"></div>
    `;
    container.appendChild(productItem);
    updateProductIndices();
}

// 删除商品输入框
function removeProduct(button) {
    const container = document.getElementById('productsContainer');
    if (container.children.length > 1) {
        button.closest('.product-item').remove();
    }
    updateProductIndices();
}

// 在创建会话时收集商品信息
async function createSession() {
    const userName = document.getElementById('userName').value.trim();
    const liveTheme = document.getElementById('liveTheme').value.trim();

    if (!userName || !liveTheme) {
        showError('请填写主播名称和直播主题');
        return;
    }

    // 收集商品信息（包含类型和属性）
    const productInputs = document.querySelectorAll('.product-item');
    const products = [];

    productInputs.forEach(rowEl => {
        const name = rowEl.querySelector('.product-name').value.trim();
        const price = rowEl.querySelector('.product-price').value.trim();
        const unit = rowEl.querySelector('.unit-select').value;
        const type = rowEl.querySelector('.product-type').value;

        // 允许不填写价格：只要有名称和类型就可创建商品（price 可为空）
        if (name && type) {
            // 收集属性信息：支持结构化子字段（data-subkey），例如 size => { value, unit }
            const attributes = {};
            const attributeInputs = rowEl.querySelectorAll('[data-key]');
            attributeInputs.forEach(input => {
                const key = input.getAttribute('data-key');
                if (!key) return;
                const subkey = input.getAttribute('data-subkey');
                // 读取值（兼容 select/input/textarea）
                let value = '';
                try { value = (input.value || '').toString().trim(); } catch (e) { value = '' }
                if (!value) return;
                if (subkey) {
                    // 创建或合并子对象
                    if (!attributes[key] || typeof attributes[key] !== 'object') attributes[key] = {};
                    attributes[key][subkey] = value;
                } else {
                    // 若之前已有子对象（来自其他 subkey），写到 .value 里以保持信息完整
                    if (attributes[key] && typeof attributes[key] === 'object') {
                        attributes[key].value = value;
                    } else {
                        attributes[key] = value;
                    }
                }
            });

            const product = {
                name: name,
                // 若未填写价格则设为 null，避免 parseFloat('') 生成 NaN
                price: price ? parseFloat(price) : null,
                unit: unit,
                type: type,
                attributes: attributes
            };
            products.push(product);
        }
    });

    if (products.length === 0) {
        showError('请至少添加一个完整的商品信息');
        return;
    }

    // 检查是否有商品没有选择类型
    const invalidProducts = products.filter(p => !p.type);
    if (invalidProducts.length > 0) {
        showError('请为所有商品选择商品类型');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                host_name: userName,
                live_theme: liveTheme,
                products: products
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentSessionId = data.session_id;
            // 保存本地类型快照，供后续根据类型调整快捷建议
            createdProductsSnapshot = products;

            // 不再保存到本地存储，每次刷新都需要重新创建会话
            // localStorage.setItem('current_session_id', currentSessionId);

            // 清空聊天记录，显示新会话的欢迎消息
            const chatContainer = document.getElementById('chatContainer');
            chatContainer.innerHTML = '';

            // 加载会话信息
            await loadSessionInfo();

            // 启用聊天功能
            document.getElementById('messageInput').disabled = false;
            document.getElementById('sendButton').disabled = false;
            document.getElementById('suggestionButtons').style.display = 'flex';

            // 隐藏错误信息
            document.getElementById('errorMessage').style.display = 'none';

            // 更新状态
            document.getElementById('status').textContent = '✅ 会话创建成功！可以开始生成直播话术了';
            document.getElementById('status').style.background = '#d4edda';

            // 显示会话信息
            document.getElementById('sessionInfo').style.display = 'block';

            // 创建成功后自动折叠左侧商品面板
            setSidebarCollapsed(true);
            // 根据商品类型调整快捷按钮文案
            updateSuggestionButtonsUI();

        } else {
            showError(data.error || '创建会话失败');
        }
    } catch (error) {
        showError('网络错误，请检查服务器连接');
        console.error('创建会话错误:', error);
    }
}
// 加载会话信息时显示完整价格信息
async function loadSessionInfo() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`${API_BASE}/api/session/${currentSessionId}`);
        const data = await response.json();

        if (response.ok) {
            sessionInfo = data;

            // 显示会话信息
            document.getElementById('sessionDetails').textContent =
                `${data.host_name} - ${data.live_theme}`;

            // 不自动加载对话历史，只显示欢迎消息
            const productsText = data.products.map(p =>
                (p.price !== undefined && p.price !== null) ? `${p.product_name}：${p.price}${p.unit || '元'}` : `${p.product_name}`
            ).join('、');

            addMessage('assistant', `太好了！${data.host_name}，我已经了解了你的直播信息：
            
直播主题：${data.live_theme}
售卖商品：${productsText}

现在我可以为你生成专业的直播话术了！你可以直接输入需求，或者点击下方的快捷按钮。`);

            // 填充快捷建议的商品选择下拉
            populateSuggestionProducts(sessionInfo.products || []);
            const box = document.getElementById('suggestionProductBox');
            if (box) box.style.display = 'inline-flex';
            // 初始根据第一个商品类型调整按钮
            updateSuggestionButtonsUI();

            // 将服务端返回的 products 同步回左侧商品表单（若存在）
            try {
                applySessionProductsToForm();
            } catch (e) {
                console.warn('同步会话商品到表单失败：', e);
            }


        } else {
            console.error('加载会话信息失败:', data.error);
        }

    } catch (error) {
        console.error('加载会话信息错误:', error);
    }
}

// 开启新对话
function startNewConversation() {
    if (!currentSessionId) return;
    
    if (!confirm('确定要开启新对话吗？当前对话记录将被清空。')) {
        return;
    }
    
    // 清空聊天容器
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = '';
    
    // 显示欢迎消息（使用当前会话信息）
    if (sessionInfo) {
        const productsText = sessionInfo.products.map(p =>
            `${p.product_name}：${p.price}${p.unit || '元'}`
        ).join('、');

        addMessage('assistant', `开启新对话！${sessionInfo.host_name}，让我们重新开始：
        
直播主题：${sessionInfo.live_theme}
售卖商品：${productsText}

你可以直接输入需求，或者点击下方的快捷按钮获取话术建议。`);
    }
    
    // 聚焦到输入框
    document.getElementById('messageInput').focus();
}

// 发送快捷建议请求
// 更新快捷建议请求
function askSuggestion(type) {
    let message = '';
    const sel = document.getElementById('suggestionProductSelect');
    let index = 1;
    let name = '';
    let ptype = '';
    if (sel && sel.value) {
        index = parseInt(sel.value, 10) || 1;
    }
    if (sessionInfo && Array.isArray(sessionInfo.products)) {
        const item = sessionInfo.products[index - 1];
        if (item) name = item.product_name || '';
    }
    ptype = getProductTypeByIndex(index) || '';
    message = buildSuggestionPrompt(type, ptype, index, name);

    // 将建议填入输入框并聚焦，但不自动发送，方便用户查看或编辑后再发送
    const msgInput = document.getElementById('messageInput');
    if (msgInput) {
        msgInput.value = message;
        msgInput.focus();
    }
}

function populateSuggestionProducts(products) {
    const sel = document.getElementById('suggestionProductSelect');
    if (!sel) return;
    sel.innerHTML = '';
    if (!Array.isArray(products) || products.length === 0) return;
    products.forEach((p, idx) => {
        const opt = document.createElement('option');
        opt.value = String(idx + 1);
        opt.textContent = `${idx + 1} - ${p.product_name || ''}`;
        sel.appendChild(opt);
    });
}

// 从 /api/tts/tts-<hash>.wav 提取文件名
function extractTTSFileId(audioUrl) {
    try {
        const u = new URL(audioUrl, window.location.origin);
        const parts = u.pathname.split('/');
        return parts[parts.length - 1] || '';
    } catch (e) {
        return '';
    }
}

// 短轮询等待 TTS 就绪，避免刚开始就触发404
async function waitForTTSReady(audioUrl, maxWaitMs = 1500, pollIntervalMs = 150) {
    const start = Date.now();
    const file = extractTTSFileId(audioUrl);
    if (!file || !file.startsWith('tts-')) return; // 无法识别则直接返回
    while (Date.now() - start < maxWaitMs) {
        try {
            const resp = await fetch(`${API_BASE}/api/tts/status?file=${encodeURIComponent(file)}`, { cache: 'no-store' });
            if (!resp.ok) break; // 端点不可用则直接跳出
            const data = await resp.json();
            if (data && data.ready) return; // 就绪
            // 未就绪则短暂等待
        } catch (e) {
            break; // 网络或其他问题，直接跳出，后续走audio自带重试
        }
        await new Promise(r => setTimeout(r, pollIntervalMs));
    }
}

// 发送消息
async function sendMessage() {
    if (!currentSessionId) {
        showError('请先创建会话');
        return;
    }

    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const status = document.getElementById('status');
    const message = messageInput.value.trim();

    if (!message) return;

    // 添加用户消息到界面
    addMessage('user', message);

    // 保存原始消息以便在 need_info 场景重试
    const originalMessage = message;

    // 清空输入框并禁用
    messageInput.value = '';
    messageInput.disabled = true;
    sendButton.disabled = true;
    status.textContent = '小聚正在思考...';

    try {
        const callChat = async () => {
            const resp = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    message: originalMessage
                })
            });
            return resp;
        };

        let response = await callChat();
        let data = {};
        try {
            data = await response.json();
        } catch (e) {
            console.warn('解析 /api/chat 返回 JSON 失败或返回为空', e);
            data = {};
        }
        // 调试日志：记录后端返回以便排查空响应问题
        console.debug('chat api response', { status: response.status, ok: response.ok, body: data });

            // 处理 need_info：后端要求补充商品信息（如产地）
            // 只有在后端没有同时返回可显示文本时，才发起备选请求收窄模型行为；
            // 如果后端同时返回了 "response" 字段，则优先显示该回答。
            if (response.ok && data && data.need_info && !(data.response && data.response.trim && data.response.trim().length > 0)) {
                // 检测到缺失字段：不阻止回答，先告知用户并基于现有信息继续尝试回答
                const rawKey = data.info_key || '';
                const infoKey = translateInfoKey(rawKey);
                const candidates = data.product_candidates || [];
                const productList = (Array.isArray(candidates) && candidates.length > 0) ? ('可选商品：' + candidates.map((c, i) => `${i+1}. ${c}`).join('，') + '。') : '';
                // 不在 UI 中提示缺失字段，保持界面简洁；在控制台记录以便调试
                console.warn(`缺失字段 ${infoKey}，将基于现有信息继续回答。 ${productList}`);

                // 发送一次带有明确指令的备选请求，要求模型基于当前已知信息回答而不再请求补充
                try {
                    const fallbackMessage = originalMessage + "\n\n（请基于现有已知信息尽量回答，不要要求补充。）";
                    const resp2 = await fetch(`${API_BASE}/api/chat`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: currentSessionId, message: fallbackMessage })
                    });
                    response = resp2;
                    data = await response.json();
                } catch (e) {
                    console.warn('备选请求失败，继续使用原始响应', e);
                }
                // 继续到后续处理（不再直接 return）
            }

        if (response.ok) {
            // 若响应中未包含可显示文本，使用占位提示并在控制台输出完整返回，便于定位原因
            const assistantText = (data && typeof data.response === 'string' && data.response.trim().length > 0)
                ? data.response
                : (data && data.error) ? `(错误) ${data.error}` : '(未返回文本)';
            if (!data || !data.response) {
                console.warn('收到空的 AI 响应文本，已在界面显示占位。完整返回：', data);
            }
            addMessage('assistant', assistantText, data && data.audio_url);
            status.textContent = '✅ 思考完毕';
        } else {
            throw new Error((data && data.error) ? data.error : '请求失败');
        }

    } catch (error) {
        console.error('发送消息错误:', error);
        addMessage('assistant', `❌ 抱歉，出现了错误：${error.message}`);
        status.textContent = '❌ 请求失败';
    } finally {
        // 重新启用输入框
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// 添加消息到聊天界面
function addMessage(role, content, audioUrl) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    // 文本
    const textP = document.createElement('p');
    textP.textContent = content;
    messageDiv.appendChild(textP);

    // 若附带语音
    if (role === 'assistant' && audioUrl) {
        const audioWrap = document.createElement('div');
        audioWrap.className = 'audio-wrap';
        const audio = document.createElement('audio');
        audio.controls = true;
        audio.preload = 'auto';
        // 自动播放（可能受浏览器自动播放策略限制）
        audio.addEventListener('canplay', () => {
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(() => {/* 静默失败，用户可手动播放 */});
            }
        });
        // 若TTS文件尚未生成或被系统短暂占用，采用指数退避重试加载（最长约20s）
        let retry = 0;
        audio.addEventListener('error', () => {
            if (retry < 15) { // 最多重试15次
                retry++;
                const delay = Math.min(5000, 400 + Math.pow(1.35, retry) * 200); // 400ms起步，指数增长，封顶5s
                setTimeout(() => {
                    const bust = `__r=${Date.now()}`;
                    const url = new URL(audioUrl, window.location.origin);
                    url.searchParams.set('__r', bust);
                    audio.src = url.pathname + url.search;
                    audio.load();
                }, delay);
            }
        });
        // 先做一次短轮询，等到ready后再首次设置src，避免一上来就是404
        waitForTTSReady(audioUrl, 1500, 150).finally(() => {
            const bust = `__r=${Date.now()}`;
            const url = new URL(audioUrl, window.location.origin);
            url.searchParams.set('__r', bust);
            audio.src = url.pathname + url.search;
            audio.load();
        });
        audioWrap.appendChild(audio);
        messageDiv.appendChild(audioWrap);
    }
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 显示错误信息
function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', function () {
    // 清除之前保存的会话，每次刷新都需要重新创建
    localStorage.removeItem('current_session_id');
    
    // 清空聊天容器
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = '';
    
    // 显示欢迎提示
    addMessage('assistant', '👋 欢迎使用专业版直播销售助手！请先在左侧配置直播信息，创建会话后即可开始生成专业的直播话术。');

    // 默认添加一个空商品行
    addProduct();
    updateProductIndices();

    // 回车发送消息
    document.getElementById('messageInput').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    
    // 侧边栏折叠按钮
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => setSidebarCollapsed(!sidebarCollapsed));
    }

    // 浮动快速展开按钮（仅在折叠时显示）
    const fab = document.getElementById('sidebarFab');
    if (fab) {
        fab.addEventListener('click', () => setSidebarCollapsed(false));
    }

    // 键盘快捷键：Alt+L 切换侧边栏；Alt+1..Alt+5 触发快捷建议
    window.addEventListener('keydown', (e) => {
        if (e.altKey && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
            const k = e.key.toLowerCase();
            if (k === 'l') {
                e.preventDefault();
                setSidebarCollapsed(!sidebarCollapsed);
            } else if (['1','2','3','4','5'].includes(k)) {
                e.preventDefault();
                if (!currentSessionId) return; // 未创建会话不触发
                // 从当前的快捷按钮上读取文案作为请求类型，避免硬编码带来的不一致
                try {
                    const btns = document.querySelectorAll('.suggestion-btn');
                    const idx = Math.max(0, Math.min(btns.length - 1, parseInt(k, 10) - 1));
                    const btn = btns[idx];
                    // 优先读取 data-kind（语义键），若不存在再回退到可视文本
                    const kind = (btn && btn.dataset && btn.dataset.kind) ? btn.dataset.kind : (btn && btn.textContent ? btn.textContent.trim() : '');
                    if (kind) {
                        askSuggestion(kind);
                    } else {
                        // 兜底到以前的静态映射（如果按钮不存在）
                        const fallback = {
                            '1': '产品介绍',
                            '2': '食用方法',
                            '3': 'APP功能',
                            '4': '乡村文化',
                            '5': '促销引导'
                        };
                        askSuggestion(fallback[k]);
                    }
                } catch (err) {
                    console.error('快捷键触发建议失败:', err);
                }
            }
        }
    });

    // 快捷建议下拉选改变时，动态更新按钮文案
    const sel = document.getElementById('suggestionProductSelect');
    if (sel) {
        sel.addEventListener('change', () => updateSuggestionButtonsUI());
    }

    // 已移除 need_info 弹窗交互，前端将提示用户在左侧表单补充信息后重试
});

function updateProductIndices() {
    const items = document.querySelectorAll('#productsContainer .product-item');
    items.forEach((item, idx) => {
        let badge = item.querySelector('.product-index');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'product-index';
            const basic = item.querySelector('.product-basic-info');
            if (basic) basic.prepend(badge);
        }
        badge.textContent = (idx + 1).toString();
    });
}

function setSidebarCollapsed(collapse) {
    sidebarCollapsed = collapse;
    const container = document.querySelector('.container');
    const toggleBtn = document.getElementById('sidebarToggle');
    const fab = document.getElementById('sidebarFab');
    if (!container) return;
    if (collapse) {
        container.classList.add('sidebar-collapsed');
        if (toggleBtn) toggleBtn.textContent = '⮜ 展开商品面板';
        if (toggleBtn) toggleBtn.title = '展开商品面板 (Alt+L)';
        if (fab) fab.style.display = 'block';
    } else {
        container.classList.remove('sidebar-collapsed');
        if (toggleBtn) toggleBtn.textContent = '⮞ 隐藏商品面板';
        if (toggleBtn) toggleBtn.title = '隐藏商品面板 (Alt+L)';
        if (fab) fab.style.display = 'none';
    }
}

function getProductTypeByIndex(index) {
    // 优先从服务端返回的数据读取（可能字段名 product_type 或 type）
    if (sessionInfo && Array.isArray(sessionInfo.products)) {
        const p = sessionInfo.products[index - 1];
        if (p) {
            const t = p.product_type || p.type;
            if (t) return String(t);
        }
    }
    // 回退到创建会话时的快照（保持顺序一致）
    if (Array.isArray(createdProductsSnapshot) && createdProductsSnapshot[index - 1]) {
        const t = createdProductsSnapshot[index - 1].type;
        if (t) return String(t);
    }
    return '';
}

// 按商品类型与快捷类型构建更自然的请求话术
function buildSuggestionPrompt(kind, ptype, index, name) {
    const id = `第${index}号商品${name ? `（${name}）` : ''}`;
    const type = (ptype || '').toLowerCase();
    const K = kind;

    // helper: 获取商品对象（优先 sessionInfo，其次本地快照）
    function _getProductObj(idx) {
        if (sessionInfo && Array.isArray(sessionInfo.products)) {
            return sessionInfo.products[idx - 1] || null;
        }
        if (Array.isArray(createdProductsSnapshot)) {
            return createdProductsSnapshot[idx - 1] || null;
        }
        return null;
    }

    // helper: 将 attributes 转为简短的已知信息摘要（只包含有值的字段）
    function _summarizeAttributes(prod) {
        if (!prod) return '';
        const parts = [];
        // 常见顶层信息
        const pname = prod.product_name || prod.name || '';
        const price = (prod.price || prod.price === 0) ? `${prod.price}${prod.unit || '元'}` : '';
        if (price) parts.push(`价格：${price}`);

    const attrs = prod.attributes || {};
    // 使用 productTypeConfig 来获取友好标签：优先根据 product_type（服务端可能返回此字段），其次再用 type
    const ptype = prod.product_type || prod.type || '';
    const cfg = (productTypeConfig && ptype && productTypeConfig[ptype]) ? productTypeConfig[ptype] : null;
        for (const k of Object.keys(attrs)) {
            let v = attrs[k];
            if (v === null || v === undefined || v === '') continue;
            if (typeof v === 'object') {
                // 合并子字段（如尺寸）
                v = Object.values(v).filter(Boolean).join(' ');
            }
            const label = (cfg && cfg.attributes && cfg.attributes.find(a => a.key === k) && cfg.attributes.find(a => a.key === k).label) || k;
            parts.push(`${label.replace(/\s*（.*?）/, '')}：${v}`);
            if (parts.length >= 6) break; // 防止过长
        }
        if (parts.length === 0 && pname) return `商品名：${pname}`;
        return parts.join('；');
    }

    // 基础模板（保留简洁版本）
    const baseTemplates = {
        productIntro: `请简要介绍${id}的核心卖点和必要信息，语言亲切，约100-150字。`,
        usage: `给出${id}的实用食用/使用方法和要点，简洁明确。`,
        culture: `用120字以内讲一个与${id}相关的产地或工艺小故事，突出人情味。`,
        promo: `给出简短促销话术，提醒新鲜/数量/查看详情，避免夸大。`,
        app: `简要说明乡聚APP的下单-取货-售后关键步骤，便于用户理解。`
    };

    // 特例：APP功能
    if (K === 'APP功能') return baseTemplates.app;

    // 选择模板类型
    let promptCore = baseTemplates.productIntro;
    const kmap = {
        '产品介绍': 'productIntro',
        '食用方法': 'usage',
        '使用与保养建议': 'usage',
        '乡村文化': 'culture',
        '促销引导': 'promo',
    };
    if (kmap[K]) promptCore = baseTemplates[kmap[K]];

    // 获取已知信息摘要并只在存在时追加，要求只使用这些信息
    const prodObj = _getProductObj(index);
    const summary = _summarizeAttributes(prodObj);
    if (summary) {
        return `${promptCore}\n已知信息：${summary}。仅基于这些信息生成话术，若信息不足请说明缺失项。`;
    }

    return promptCore;
}

// 根据选中的商品类型，动态调整快捷按钮的文案与提示
function updateSuggestionButtonsUI() {
    const sel = document.getElementById('suggestionProductSelect');
    let index = 1;
    if (sel && sel.value) index = parseInt(sel.value, 10) || 1;
    const type = (getProductTypeByIndex(index) || '').toLowerCase();
    const box = document.querySelector('.suggestion-buttons');
    if (!box) return;
    const btns = box.querySelectorAll('.suggestion-btn');
    if (!btns || btns.length < 5) return;
    const btnIntro = btns[0];
    const btnUsage = btns[1];
    const btnApp = btns[2];
    const btnCulture = btns[3];
    const btnPromo = btns[4];

    // 默认
    let introLabel = '📦 产品介绍';
    let usageLabel = '🍳 食用方法';
    let cultureLabel = '🏡 乡村文化';
    // 根据类型替换更贴切的标签
    if (type === 'handicraft') {
        introLabel = '🎨 工艺亮点';
        usageLabel = '🧴 使用与保养建议';
        cultureLabel = '🏺 文化故事';
    } else if (type === 'processed') {
        usageLabel = '🍽️ 吃法搭配';
    } else if (type === 'grain') {
        usageLabel = '🥣 烹煮要点';
    }
    btnIntro.textContent = introLabel;
    btnUsage.textContent = usageLabel;
    btnApp.textContent = '📱 APP功能';
    btnCulture.textContent = cultureLabel;
    btnPromo.textContent = '💬 促销引导';
    // 更新title以反映快捷键
    const titles = ['Alt+1', 'Alt+2', 'Alt+3', 'Alt+4', 'Alt+5'];
    [btnIntro, btnUsage, btnApp, btnCulture, btnPromo].forEach((b, i) => b.title = titles[i]);
    // 设置语义性的 data-kind，供快捷键触发时读取（避免使用带 emoji 的可视文本）
    try {
        btnIntro.dataset.kind = '产品介绍';
        // 使用与保养建议仅在手工艺品类型使用，其余食物类使用 '食用方法'
        btnUsage.dataset.kind = (type === 'handicraft') ? '使用与保养建议' : '食用方法';
        btnApp.dataset.kind = 'APP功能';
        btnCulture.dataset.kind = '乡村文化';
        btnPromo.dataset.kind = '促销引导';
    } catch (e) {
        // 某些旧浏览器或环境下 dataset 可能不存在，静默回退
    }
    // 覆盖按钮点击处理：优先使用 data-kind，保证按钮点击与快捷键行为一致
    try {
        btnIntro.onclick = () => askSuggestion(btnIntro.dataset && btnIntro.dataset.kind ? btnIntro.dataset.kind : btnIntro.textContent.trim());
        btnUsage.onclick = () => askSuggestion(btnUsage.dataset && btnUsage.dataset.kind ? btnUsage.dataset.kind : btnUsage.textContent.trim());
        btnApp.onclick = () => askSuggestion(btnApp.dataset && btnApp.dataset.kind ? btnApp.dataset.kind : btnApp.textContent.trim());
        btnCulture.onclick = () => askSuggestion(btnCulture.dataset && btnCulture.dataset.kind ? btnCulture.dataset.kind : btnCulture.textContent.trim());
        btnPromo.onclick = () => askSuggestion(btnPromo.dataset && btnPromo.dataset.kind ? btnPromo.dataset.kind : btnPromo.textContent.trim());
    } catch (e) {
        // 静默回退，不影响页面可用性
    }
}

// 将 sessionInfo.products 的数据填回左侧的商品输入表单，保持界面与服务端一致
function applySessionProductsToForm() {
    if (!sessionInfo || !Array.isArray(sessionInfo.products)) return;
    const container = document.getElementById('productsContainer');
    if (!container) return;
    const items = container.querySelectorAll('.product-item');

    sessionInfo.products.forEach((p, idx) => {
        const item = items[idx];
        if (!item) return;
        const nameInput = item.querySelector('.product-name');
        const priceInput = item.querySelector('.product-price');
        const unitSelect = item.querySelector('.unit-select');
        const typeSelect = item.querySelector('.product-type');

    if (nameInput) nameInput.value = p.product_name || p.name || '';
    if (priceInput) priceInput.value = (p.price !== undefined && p.price !== null) ? p.price : '';
        if (unitSelect && p.unit) unitSelect.value = p.unit;
        const t = p.product_type || p.type || '';
        if (typeSelect) {
            typeSelect.value = t;
            // 触发属性区重渲染
            if (t) updateProductAttributes(typeSelect);
        }

        // 填充属性值（支持子字段和对象）
        const attrs = p.attributes || {};
        // 查找刚渲染出的属性输入控件并赋值
        const attrInputs = item.querySelectorAll('[data-key]');
        attrInputs.forEach(inp => {
            const key = inp.getAttribute('data-key');
            const subkey = inp.getAttribute('data-subkey');
            if (!key) return;
            const val = attrs[key];
            if (val === undefined || val === null || val === '') {
                try { inp.value = ''; } catch (e) {}
                return;
            }
            let setVal = '';
            if (typeof val === 'object') {
                if (subkey) {
                    setVal = val[subkey] || '';
                } else {
                    setVal = val.value || Object.values(val).filter(Boolean).join(' ') || '';
                }
            } else {
                setVal = String(val);
            }
            try { inp.value = setVal; } catch (e) {}
        });
    });

    // 更新本地创建时的快照，保持 prompt 构建时的回退一致性
    try {
        createdProductsSnapshot = sessionInfo.products.map(p => ({
            name: p.product_name || p.name || '',
            price: p.price || '',
            unit: p.unit || '',
            type: p.product_type || p.type || '',
            attributes: p.attributes || {}
        }));
    } catch (e) {
        // 静默处理非关键错误
    }
}

// 将后端要求补充字段（info_key）翻译为用户可读的中文标签
function translateInfoKey(key) {
    if (!key) return '信息';
    const map = {
        origin: '产地',
        price: '价格',
        sweetness: '甜度',
        harvest_date: '采摘日期',
        slaughter_date: '宰杀/处理日期',
        size: '尺寸',
        variety: '品种',
        storage: '储存建议'
    };
    return map[key] || key;
}

// 将单个商品的某个字段保存到服务端（用于自动保存属性变更）
async function saveProductInfoToServer(sessionId, productName, key, value) {
    if (!sessionId || !productName || !key) return;
    try {
        const resp = await fetch(`${API_BASE}/api/session/product-info`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, product_name: productName, key: key, value: value })
        });
        if (resp.ok) {
            // 刷新会话信息以获取服务端合并后的 attributes，并同步回表单
            try { await loadSessionInfo(); } catch (e) { console.warn('保存后刷新会话失败', e); }
        } else {
            const data = await resp.json().catch(() => ({}));
            console.warn('保存商品信息失败:', data.error || resp.statusText);
        }
    } catch (e) {
        console.error('保存商品信息网络错误：', e);
    }
}