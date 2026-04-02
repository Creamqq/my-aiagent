from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import json
import time
import hashlib
import asyncio
from contextlib import asynccontextmanager
from openai import OpenAI
from sqlalchemy.orm import Session
from datetime import datetime
from database import init_db, get_db, Chat, Message as DBMessage, ModelConfig, FeatureModelMapping, SysUser, FinanceConfig, SessionLocal, engine, ChartImage
from config import settings
from tool_codes import TOOL_CODES, get_tool_code, generate_kline_chart, generate_tick_chart

# 对话历史存储 - 内存缓存
class ConversationCache:
    def __init__(self, max_size=100, expire_time=3600):
        """初始化缓存
        max_size: 最大缓存对话数
        expire_time: 缓存过期时间（秒）
        """
        self.cache = {}
        self.max_size = max_size
        self.expire_time = expire_time
    
    def get(self, chat_id, user_id='global'):
        """获取缓存的对话历史"""
        key = f"{user_id}:{chat_id}"
        if key in self.cache:
            data, timestamp = self.cache[key]
            # 检查是否过期
            if time.time() - timestamp < self.expire_time:
                return data
            # 过期则删除
            del self.cache[key]
        return None
    
    def set(self, chat_id, user_id, data):
        """设置缓存的对话历史"""
        key = f"{user_id}:{chat_id}"
        # 如果缓存已满，删除最早的项
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        # 存储数据和时间戳
        self.cache[key] = (data, time.time())
    
    def delete(self, chat_id, user_id='global'):
        """删除缓存的对话历史"""
        key = f"{user_id}:{chat_id}"
        if key in self.cache:
            del self.cache[key]

# 初始化对话缓存
conversation_cache = ConversationCache()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    engine.dispose()

app = FastAPI(lifespan=lifespan)

# 允许CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 中间件：为JSON响应添加charset=utf-8
@app.middleware("http")
async def add_charset_header(request, call_next):
    response = await call_next(request)
    if response.headers.get("Content-Type") == "application/json":
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# 安全配置
security = HTTPBasic()
ADMIN_USERNAME = settings.ADMIN_USERNAME if hasattr(settings, 'ADMIN_USERNAME') else "admin"
ADMIN_PASSWORD = settings.ADMIN_PASSWORD if hasattr(settings, 'ADMIN_PASSWORD') else "password"

# 请求速率限制
request_counts = {}
RATE_LIMIT = 60  # 每分钟最大请求数

# 身份验证
async def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = credentials.username == ADMIN_USERNAME
    correct_password = credentials.password == ADMIN_PASSWORD
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# 速率限制
async def rate_limit():
    client_ip = "127.0.0.1"  # 在生产环境中应该从请求中获取真实IP
    current_time = time.time()
    
    if client_ip not in request_counts:
        request_counts[client_ip] = []
    
    # 清理过期的请求记录
    request_counts[client_ip] = [t for t in request_counts[client_ip] if current_time - t < 60]
    
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    request_counts[client_ip].append(current_time)
    return True

# 获取模型配置
def get_model_config(model_name, user_id='global'):
    """从数据库获取模型配置"""
    db = None
    try:
        print(f"获取模型配置: {model_name}, 用户: {user_id}")
        
        db = SessionLocal()
        
        model_config = db.query(ModelConfig).filter(
            ModelConfig.user_id == user_id,
            ModelConfig.name == model_name,
            ModelConfig.status == 1
        ).first()
        
        if not model_config:
            model_config = db.query(ModelConfig).filter(
                ModelConfig.user_id == 'global',
                ModelConfig.name == model_name,
                ModelConfig.status == 1
            ).first()
        
        if model_config:
            result = {
                "name": model_config.name,
                "apiKey": model_config.api_key,
                "apiUrl": model_config.api_url
            }
            print(f"从数据库找到模型配置: {result['name']}")
            return result
    except Exception as e:
        print(f"获取模型配置失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
    finally:
        if db:
            db.close()
    
    default_config = {
        "name": model_name,
        "apiKey": settings.DASHSCOPE_API_KEY,
        "apiUrl": "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
    }
    print(f"返回默认配置: {default_config}")
    return default_config

# 获取功能模型映射
def get_feature_model_mapping(feature_name, user_id='global'):
    """从数据库获取功能模型映射"""
    db = None
    try:
        db = SessionLocal()
        
        mapping = db.query(FeatureModelMapping).filter(
            FeatureModelMapping.feature_name == feature_name,
            FeatureModelMapping.user_id == user_id,
            FeatureModelMapping.status == 1
        ).first()
        
        if not mapping:
            mapping = db.query(FeatureModelMapping).filter(
                FeatureModelMapping.feature_name == feature_name,
                FeatureModelMapping.user_id == 'global',
                FeatureModelMapping.status == 1
            ).first()
        
        return mapping
    except Exception as e:
        print(f"获取功能模型映射失败: {e}")
        return None
    finally:
        if db:
            db.close()

# 更新功能模型映射
def update_feature_model_mapping(feature_name, model_name, user_id='global'):
    """更新功能模型映射"""
    db = None
    try:
        db = SessionLocal()
        
        mapping = db.query(FeatureModelMapping).filter(
            FeatureModelMapping.feature_name == feature_name,
            FeatureModelMapping.user_id == user_id
        ).first()
        
        if mapping:
            mapping.model_name = model_name
            mapping.status = 1
        else:
            mapping = FeatureModelMapping(
                feature_name=feature_name,
                model_name=model_name,
                user_id=user_id,
                status=1
            )
            db.add(mapping)
        
        db.commit()
        return True
    except Exception as e:
        print(f"更新功能模型映射失败: {e}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()

# 生成对话标题
async def generate_chat_title(content, db):
    """根据对话内容生成标题"""
    try:
        # 获取用于生成标题的模型
        mapping = get_feature_model_mapping('chat_title')
        if not mapping:
            # 如果没有配置，使用默认模型
            print(f"标题生成模型未配置")
            return f"新对话"
        else:
            model_name = mapping.model_name
        
        # 获取模型配置
        model_config = get_model_config(model_name)
        api_key = str(model_config.get("apiKey", settings.DASHSCOPE_API_KEY))
        api_url = str(model_config.get("apiUrl", "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"))
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_url
        )
        
        # 构建提示词
        prompt = f"请为以下对话内容生成一个简短、准确的标题，不超过10个字符：\n{content}"
        
        # 构建请求参数
        title_create_params = {
            "model": model_name,
            "input": [{"role": "user", "content": prompt}],
            "stream": False,
            "extra_body": {
                "enable_thinking": False
            }
        }
        
        # 打印完整的请求参数
        print("=== 生成标题 - 发送给大模型的完整请求参数 ===")
        print(json.dumps(title_create_params, ensure_ascii=False, indent=2))
        print("===================================")
        
        # 发送请求
        response = client.responses.create(**title_create_params)
        
        # 提取标题
        title = response.output_text.strip()
        if len(title) > 15:
            title = title[:15]
        
        return title
    except Exception as e:
        print(f"生成对话标题失败: {e}")
        # 如果生成失败，返回默认标题
        return f"新对话"

# OpenAI兼容的请求模型
class Message(BaseModel):
    role: str
    content: str

class tool_function(BaseModel): 
    parameters: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None

class Tool(BaseModel):
    model_config = {"protected_namespaces": ()}
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    server_protocol: Optional[str] = None
    server_label: Optional[str] = None
    server_description: Optional[str] = None
    server_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    function: Optional[tool_function] = None


class ToolChoice(BaseModel):
    type: str
    function: Optional[Dict[str, Any]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = True  # 默认开启流式输出，提高响应速度体验
    top_p: Optional[float] = 1.0
    # Responses API 特有参数
    instructions: Optional[str] = None
    previous_response_id: Optional[str] = None
    conversation: Optional[str] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, ToolChoice]] = None
    enable_thinking: Optional[bool] = False
    user_id: Optional[str] = None  # 用户ID，用于获取个人模型配置

# OpenAI兼容的响应模型
class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Dict[str, int]
    output: Optional[List[Dict[str, Any]]] = None

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, db: Session = Depends(get_db)):
    try:
        # 先记录基本信息
        print("=== 接收聊天请求 ===")
        print(f"请求模型: {request.model}")
        print(f"请求消息: {[msg.model_dump() for msg in request.messages]}")
        
        # 从 conversation 字段解析出 chat_id（格式为 chat_{id} 或 finance_{id}）
        chat_id = None
        if request.conversation:
            if request.conversation.startswith("chat_"):
                try:
                    chat_id = int(request.conversation.split("_")[1])
                except:
                    pass
            elif request.conversation.startswith("finance_"):
                try:
                    chat_id = int(request.conversation.split("_")[1])
                except:
                    pass
        
        # 如果有有效的 chat_id，从缓存或数据库加载对话历史
        conversation_history_list = []
        if chat_id:
            user_id = request.user_id or 'global'
            # 先尝试从缓存获取
            cached_history = conversation_cache.get(chat_id, user_id)
            if cached_history:
                conversation_history_list = cached_history
                print(f"从缓存加载对话历史，共 {len(conversation_history_list)} 条消息")
            else:
                # 缓存未命中，从数据库加载（只查询状态为正常的对话）
                chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
                if chat:
                    messages = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).all()
                    conversation_history_list = [{"role": msg.role, "content": msg.content} for msg in messages]
                    print(f"从数据库加载对话历史，共 {len(conversation_history_list)} 条消息")
                    # 将历史存入缓存
                    conversation_cache.set(chat_id, user_id, conversation_history_list)
        
        # 添加新请求的消息到历史（用于 API 调用）
        if chat_id:
            # 如果有chat_id，只添加最后一条消息（新的用户请求）
            if request.messages:
                conversation_history_list.append(request.messages[-1].model_dump())
        else:
            # 如果没有chat_id，添加所有消息
            for msg in request.messages:
                conversation_history_list.append(msg.model_dump())
        
        # 获取模型配置，传递 user_id 以获取个人配置
        try:
            user_id = request.user_id or 'global'
            print(f"使用用户ID获取模型配置: {user_id}")
            model_config = get_model_config(request.model, user_id)
            # 确保 api_key 和 api_url 是字符串类型
            api_key = str(model_config.get("apiKey", settings.DASHSCOPE_API_KEY))
            api_url = str(model_config.get("apiUrl", "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"))
            print(f"模型配置 - API URL: {api_url}")
            print(f"模型配置 - API Key: {'****' if api_key else '未配置'}")
        except Exception as e:
            print(f"获取模型配置时出错: {str(e)}")
            raise
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_url
        )
        
        # 准备输入数据
        # input 应该是完整的消息数组
        input_data = conversation_history_list
        
        print(f"准备的输入数据: {json.dumps(input_data, ensure_ascii=False)}")
        
        # 发送请求
        try:
            print("正在发送请求到API...")
            
            # 检查是否需要流式输出
            if request.stream:
                print("使用流式输出模式")
                # 流式请求
                create_params = {
                    "model": request.model,
                    "input": input_data if input_data is not None and len(input_data) > 0 else [{"role": "user", "content": "请回复"}],  # type: ignore
                    "stream": True,
                }
                
                # 添加可选参数，只添加非None的值
                if request.temperature is not None:
                    create_params["temperature"] = request.temperature
                if request.top_p is not None:
                    create_params["top_p"] = request.top_p
                if request.instructions is not None:
                    create_params["instructions"] = request.instructions
                if request.previous_response_id is not None:
                    create_params["previous_response_id"] = request.previous_response_id
                if request.tools is not None and len(request.tools) > 0:
                    create_params["tools"] = [tool.model_dump(exclude_none=True) for tool in request.tools]
                if request.tool_choice is not None:
                    create_params["tool_choice"] = request.tool_choice
                # 确保enable_thinking参数在为false时也能在请求中传递
                create_params["extra_body"] = {"enable_thinking": request.enable_thinking if request.enable_thinking is not None else False}
                
                # 打印完整的请求参数
                print("=== 发送给大模型的完整请求参数 ===")
                print(json.dumps(create_params, ensure_ascii=False, indent=2))
                print("===================================")
                
                stream = client.responses.create(**create_params)
                print(f"流式响应对象: {stream}")
                # 实时处理流式响应
                async def stream_response():
                    try:
                        chunk_id = f"chatcmpl-{int(time.time())}"
                        chunk_created = int(time.time())
                        accumulated_content = ""
                        accumulated_reasoning = ""
                        reasoning_dict = {}
                        search_sources_list = []
                        current_reasoning_index = 0
                        details_parts = []
                        
                        print("开始处理流式响应...")
                        
                        for event in stream:
                            print(f"[STREAM EVENT] {event}")
                            if event.type == 'response.output_item.done' and event.item.type == 'function_call':
                                function_call = event.item.name
                                function_args = {}
                                if hasattr(event.item, 'arguments'):
                                    try:
                                        function_args = json.loads(event.item.arguments) if event.item.arguments else {}
                                    except:
                                        function_args = {}
                                print(f"函数调用: {function_call}, 参数: {function_args}")
                                
                                tool_info = get_tool_code(function_call)
                                if tool_info:
                                    tool_params = tool_info.get("params", {})
                                    all_params = {}
                                    for param_name, param_info in tool_params.items():
                                        if param_name == "user_id":
                                            continue
                                        param_value = function_args.get(param_name, "")
                                        if param_value == "" and "default" in param_info:
                                            param_value = param_info["default"]
                                        all_params[param_name] = {
                                            "type": param_info.get("type", "string"),
                                            "description": param_info.get("description", ""),
                                            "value": param_value,
                                            "enum": param_info.get("enum"),
                                            "enum_labels": param_info.get("enum_labels")
                                        }
                                    
                                    chunk_response = {
                                        "id": chunk_id,
                                        "object": "chat.completion.chunk",
                                        "created": chunk_created,
                                        "model": request.model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {
                                                "role": "assistant",
                                                "function_call_request": {
                                                    "name": function_call,
                                                    "display_name": tool_info["name"],
                                                    "description": tool_info["description"],
                                                    "code": tool_info["code"],
                                                    "params": all_params,
                                                    "strategy_codes": tool_info.get("strategy_codes")
                                                }
                                            },
                                            "finish_reason": None
                                        }]
                                    }
                                    yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0)
                                
                            if event.type == 'response.output_text.delta':
                                text = event.delta
                                if text:
                                    accumulated_content += text
                                    chunk_response = {
                                        "id": chunk_id,
                                        "object": "chat.completion.chunk",
                                        "created": chunk_created,
                                        "model": request.model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {"role": "assistant", "content": text},
                                            "finish_reason": None
                                        }]
                                    }
                                    yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0)
                            elif event.type == 'response.web_search_call.in_progress':
                                # 联网搜索开始
                                chunk_response = {
                                    "id": chunk_id,
                                    "object": "chat.completion.chunk",
                                    "created": chunk_created,
                                    "model": request.model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"role": "assistant", "web_search_call": {"status": "in_progress"}},
                                        "finish_reason": None
                                    }]
                                }
                                yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0)
                            elif event.type == 'response.web_search_call.searching':
                                # 联网搜索中
                                chunk_response = {
                                    "id": chunk_id,
                                    "object": "chat.completion.chunk",
                                    "created": chunk_created,
                                    "model": request.model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"role": "assistant", "web_search_call": {"status": "searching"}},
                                        "finish_reason": None
                                    }]
                                }
                                yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0)
                            elif event.type == 'response.web_search_call.completed':
                                # 联网搜索完成
                                chunk_response = {
                                    "id": chunk_id,
                                    "object": "chat.completion.chunk",
                                    "created": chunk_created,
                                    "model": request.model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"role": "assistant", "web_search_call": {"status": "completed"}},
                                        "finish_reason": None
                                    }]
                                }
                                yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0)
                            elif event.type == 'response.output_item.done':
                                # 处理输出项完成事件，从中提取搜索来源
                                if hasattr(event, 'item') and hasattr(event.item, 'action') and hasattr(event.item.action, 'sources'):
                                    for idx, source in enumerate(event.item.action.sources):
                                        search_sources_list.append({
                                            'index': idx + 1,
                                            'url': source.get('url', '#') if isinstance(source, dict) else getattr(source, 'url', '#'),
                                            'title': source.get('title', '') if isinstance(source, dict) else getattr(source, 'title', '')
                                        })
                                    details_parts.append({"type": "search", 
                                                          "sources": search_sources_list.copy()})
                                    # 发送搜索来源到前端
                                    chunk_response = {
                                        "id": chunk_id,
                                        "object": "chat.completion.chunk",
                                        "created": chunk_created,
                                        "model": request.model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {"role": "assistant", "web_search_sources": search_sources_list.copy()},
                                            "finish_reason": None
                                        }]
                                    }
                                    yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0)
                            elif event.type == 'response.reasoning_summary_text.delta':
                                reasoning_delta = event.delta
                                if hasattr(event, 'summary_index'):
                                    summary_index = event.summary_index
                                else:
                                    # 如果没有 summary_index，使用当前索引并递增
                                    summary_index = current_reasoning_index
                                    current_reasoning_index += 1
                                if reasoning_delta:
                                    if summary_index not in reasoning_dict:
                                        reasoning_dict[summary_index] = ""
                                    reasoning_dict[summary_index] += reasoning_delta
                                    chunk_response = {
                                        "id": chunk_id,
                                        "object": "chat.completion.chunk",
                                        "created": chunk_created,
                                        "model": request.model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {"role": "assistant", "reasoning_summary_text": {"delta": reasoning_delta, "summary_index": summary_index}},
                                            "finish_reason": None
                                        }]
                                    }
                                    yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0)
                            elif event.type == 'response.reasoning_summary_text.done':
                                if hasattr(event, 'summary_index'):
                                    summary_index = event.summary_index
                                else:
                                    # 如果没有 summary_index，使用当前索引并递增
                                    summary_index = current_reasoning_index
                                    current_reasoning_index += 1
                                if hasattr(event, 'text'):
                                    reasoning_text = event.text
                                    reasoning_dict[summary_index] = reasoning_text
                                    chunk_response = {
                                        "id": chunk_id,
                                        "object": "chat.completion.chunk",
                                        "created": chunk_created,
                                        "model": request.model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {"role": "assistant", "reasoning_summary_text": {"done": True, "text": reasoning_text, "summary_index": summary_index}},
                                            "finish_reason": None
                                        }]
                                    }
                                    details_parts.append({"type": "reasoning", 
                                                          "content": reasoning_text})
                                    yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0)
                            elif event.type == 'response.completed':
                                print("流式输出完成")
                                if hasattr(event, 'response') and hasattr(event.response, 'usage'):
                                    print(f"总Token数: {event.response.usage.total_tokens}")
                        
                        # 发送结束帧
                        final_chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": chunk_created,
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        
                        # 将对话保存到数据库
                        if chat_id:
                            user_id = request.user_id or 'global'
                            # 只保存最后一条用户消息（当前消息）
                            user_content = ""
                            for msg in reversed(request.messages):
                                if msg.role == 'user':
                                    # 检查这条消息是否已经存在
                                    existing_msg = db.query(DBMessage).filter(
                                        DBMessage.chat_id == chat_id,
                                        DBMessage.role == msg.role,
                                        DBMessage.content == msg.content
                                    ).first()
                                    if not existing_msg:
                                        message = DBMessage(chat_id=chat_id, role=msg.role, content=msg.content, user_id=user_id)
                                        db.add(message)
                                    user_content = msg.content
                                    break  # 只处理最后一条用户消息
                            
                            # 当有助手回复内容或深度思考内容时保存
                            if accumulated_content or details_parts:
                                # 将 details 数组转为 JSON 字符串保存
                                details_content = json.dumps(details_parts) if details_parts else None
                                
                                # 将回答内容保存到 content 字段（纯文本，不含HTML）
                                answer_content = accumulated_content or ""
                                
                                # 保存助手回复，区分回答内容和详情内容
                                assistant_message = DBMessage(chat_id=chat_id, role='assistant', content=answer_content, details=details_content, user_id=user_id)
                                db.add(assistant_message)
                            
                            # 保存到数据库
                            db.commit()
                            print(f"对话历史已保存到数据库")
                            
                            # 更新缓存
                            # 重新加载完整的对话历史
                            updated_messages = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).all()
                            updated_history = [{"role": msg.role, "content": msg.content} for msg in updated_messages]
                            conversation_cache.set(chat_id, user_id, updated_history)
                            print(f"对话历史缓存已更新")
                            
                            # 每次有新对话时更新标题（只查询状态为正常的对话）
                            chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
                            if chat and (str(chat.title) == "新对话" or str(chat.title) == ""):
                                # 生成标题
                                title = await generate_chat_title(user_content, db)
                                chat.title = title
                                db.commit()
                                print(f"对话标题已更新为: {title}")
                            
                    finally:
                        pass
                
                # 返回流式响应 - 添加headers禁用缓冲
                return StreamingResponse(
                    stream_response(), 
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
                    }
                )
            else:
                # 非流式请求
                create_params = {
                    "model": request.model,
                    "input": input_data if input_data is not None and len(input_data) > 0 else [{"role": "user", "content": "请回复"}],  # type: ignore
                    "stream": False,
                }
                
                # 添加可选参数，只添加非None的值
                if request.temperature is not None:
                    create_params["temperature"] = request.temperature
                if request.top_p is not None:
                    create_params["top_p"] = request.top_p
                if request.instructions is not None:
                    create_params["instructions"] = request.instructions
                if request.previous_response_id is not None:
                    create_params["previous_response_id"] = request.previous_response_id
                if request.tools is not None and len(request.tools) > 0:
                    create_params["tools"] = [tool.model_dump(exclude_none=True) for tool in request.tools]
                if request.tool_choice is not None:
                    create_params["tool_choice"] = request.tool_choice
                # 确保enable_thinking参数在为false时也能在请求中传递
                create_params["extra_body"] = {"enable_thinking": request.enable_thinking if request.enable_thinking is not None else False}
                
                # 打印完整的请求参数
                print("=== 发送给大模型的完整请求参数 ===")
                print(json.dumps(create_params, ensure_ascii=False, indent=2))
                print("===================================")
                
                response = client.responses.create(**create_params)
                
                print(f"API响应: {response}")
                print(f"API响应ID: {response.id}")
                print(f"API响应内容: {response.output_text}")
                if hasattr(response, 'usage'):
                    print(f"API响应Token使用: {response.usage}")
                
                # 构建响应数据
                message_content = response.output_text
                response_id = response.id
                created = int(time.time())
                model = request.model
                usage = {
                    "prompt_tokens": response.usage.input_tokens if hasattr(response, 'usage') and hasattr(response.usage, 'input_tokens') else 0,
                    "completion_tokens": response.usage.output_tokens if hasattr(response, 'usage') and hasattr(response.usage, 'output_tokens') else 0,
                    "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens') else 0
                }
                
                # 构建 output 数组，包含深度思考内容
                output = []
                
                # 检查是否有深度思考内容以及联网搜索
                for item in response.output:
    # 判断是否为推理内容项
                    if hasattr(item, 'type') and item.type == 'reasoning':
                        # 或者更精确地判断类型：isinstance(item, ResponseReasoningItem)
                        reasoning_item = {
                            "type": "reasoning",
                            "id": f"reasoning_{response_id}_{len(output)}",  # 保证唯一性
                            "summary": [
                                {
                                    "type": summary.type,
                                    "text": summary.text
                                }
                                for summary in item.summary  # 提取所有 summary 文本
                            ]
                        }
                        output.append(reasoning_item)

                    if hasattr(item, 'type') and item.type == 'web_search_call':
                        sources = []
                        if hasattr(item, 'action') and hasattr(item.action, 'sources'):
                            sources = item.action.sources
                        elif hasattr(item, 'sources'):
                            sources = item.sources
                        web_search_item = {
                            "type": "search",
                            "id": f"web_search_{response_id}_{len(output)}",
                            "sources": sources
                        }
                        output.append(web_search_item)
                # 添加消息内容
                message_item = {
                    "type": "message",
                    "id": f"message_{response_id}",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {
                            "text": message_content
                        }
                    ]
                }
                output.append(message_item)
                
                # 将对话保存到数据库
                if chat_id:
                    user_id = request.user_id or 'global'
                    # 只保存最后一条用户消息（当前消息）
                    user_content = ""
                    for msg in reversed(request.messages):
                        if msg.role == 'user':
                            # 检查这条消息是否已经存在
                            existing_msg = db.query(DBMessage).filter(
                                DBMessage.chat_id == chat_id,
                                DBMessage.role == msg.role,
                                DBMessage.content == msg.content
                            ).first()
                            if not existing_msg:
                                message = DBMessage(chat_id=chat_id, role=msg.role, content=msg.content, user_id=user_id)
                                db.add(message)
                            user_content = msg.content
                            break  # 只处理最后一条用户消息
                    
                    # 构建 details 数组，按顺序保存推理和搜索内容（不包含HTML标签）
                    details_parts = []
                    for item in response.output:
                        if hasattr(item, 'type') and item.type == 'reasoning':
                            if hasattr(item, 'summary') and item.summary:
                                reasoning_text = ''.join([s.text for s in item.summary if hasattr(s, 'text') and s.text])
                                if reasoning_text:
                                    details_parts.append({
                                        "type": "reasoning",
                                        "content": reasoning_text
                                    })
                        elif hasattr(item, 'type') and item.type == 'web_search_call':
                            sources = []
                            if hasattr(item, 'action') and hasattr(item.action, 'sources'):
                                sources = item.action.sources
                            elif hasattr(item, 'sources'):
                                sources = item.sources
                            if sources:
                                sources_data = []
                                for idx, source in enumerate(sources):
                                    url = getattr(source, 'url', '#')
                                    title = getattr(source, 'title', '') or url.split('/')[2].replace('www.', '') if url != '#' else f'来源 {idx + 1}'
                                    sources_data.append({
                                        "index": idx + 1,
                                        "url": url,
                                        "title": title
                                    })
                                details_parts.append({
                                    "type": "search",
                                    "sources": sources_data
                                })
                    
                    # 当有助手回复内容或深度思考内容时保存
                    if message_content or details_parts:
                        # 将 details 数组转为 JSON 字符串保存
                        details_content = json.dumps(details_parts) if details_parts else None
                        
                        # 将回答内容保存到 content 字段（纯文本，不含HTML）
                        answer_content = message_content or ""
                        
                        # 保存助手回复，区分回答内容和详情内容
                        assistant_message = DBMessage(chat_id=chat_id, role='assistant', content=answer_content, details=details_content, user_id=user_id)
                        db.add(assistant_message)
                    
                    # 保存到数据库
                    db.commit()
                    print(f"对话历史已保存到数据库")
                    
                    # 更新缓存
                    # 重新加载完整的对话历史
                    updated_messages = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).all()
                    updated_history = [{"role": msg.role, "content": msg.content} for msg in updated_messages]
                    conversation_cache.set(chat_id, user_id, updated_history)
                    print(f"对话历史缓存已更新")
                    
                    # 每次有新对话时更新标题（只查询状态为正常的对话）
                    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
                    if chat and str(chat.title) == "新对话":
                        # 生成标题
                        title = await generate_chat_title(user_content, db)
                        chat.title = title
                        db.commit()
                        print(f"对话标题已更新为: {title}")
                
                print(f"最终构建的响应内容: {message_content}")
                
                # 构建响应对象
                openai_response = ChatCompletionResponse(
                    id=response_id,
                    created=created,
                    model=model,
                    choices=[
                        Choice(
                            index=0,
                            message=Message(
                                role="assistant",
                                content=message_content
                            ),
                            finish_reason="stop"
                        )
                    ],
                    usage=usage
                )
                
                # 添加 output 数组到响应
                openai_response.output = output
                
                print("=== 请求处理完成 ===")
                return openai_response
        except Exception as e:
            print(f"发送API请求时出错: {str(e)}")
            # 即使API调用失败，也返回一个错误响应，而不是让服务器崩溃
            openai_response = ChatCompletionResponse(
                id="chatcmpl-error",
                created=int(time.time()),
                model=request.model,
                choices=[
                    Choice(
                        index=0,
                        message=Message(
                            role="assistant",
                            content=f"API调用失败: {str(e)}"
                        ),
                        finish_reason="error"
                    )
                ],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            )
            print("返回错误响应")
            return openai_response
        
    except Exception as e:
        print(f"=== 错误发生 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        # 即使发生未捕获的异常，也返回一个错误响应
        openai_response = ChatCompletionResponse(
            id="chatcmpl-error",
            created=int(time.time()),
            model=request.model if 'request' in locals() else "unknown",
            choices=[
                Choice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content=f"服务器内部错误: {str(e)}"
                    ),
                    finish_reason="error"
                )
            ],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        return openai_response

@app.get("/")
async def root():
    return {"message": "教学智能体后端API"}

# 聊天历史管理API
class ChatCreateRequest(BaseModel):
    title: Optional[str] = None
    user_id: Optional[str] = 'global'
    type: Optional[int] = 1  # 1=主界面对话, 2=金融助手对话

class ChatUpdateRequest(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None

class MessageCreateRequest(BaseModel):
    role: str
    content: str
    user_id: Optional[str] = 'global'

@app.get("/api/chats")
async def get_chats(user_id: str = 'global', type: int = 1, db: Session = Depends(get_db)):
    chats = db.query(Chat).filter(Chat.user_id == user_id, Chat.type == type, Chat.status == 1).order_by(Chat.updated_at.desc()).all()
    return {
        "chats": [
            {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "created_at": chat.created_at.isoformat() if chat.created_at is not None else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at is not None else None
            }
            for chat in chats
        ]
    }

@app.post("/api/chats")
async def create_chat(request: ChatCreateRequest, db: Session = Depends(get_db)):
    if not request.title:
        title = "新对话"
    else:
        title = request.title
    
    chat = Chat(title=title, user_id=request.user_id, type=request.type or 1)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return {
        "id": chat.id,
        "title": chat.title,
        "type": chat.type,
        "created_at": chat.created_at.isoformat() if chat.created_at is not None else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at is not None else None,
        "messages": []
    }

@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: int, user_id: str = 'global', page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    # 只查询状态为正常的对话（软删除过滤）
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 计算总消息数
    total_messages = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).count()
    
    # 计算偏移量
    offset = (page - 1) * page_size
    
    # 分页查询消息
    messages = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).offset(offset).limit(page_size).all()
    
    message_list = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "details": msg.details,
            "created_at": msg.created_at.isoformat() if msg.created_at is not None else None
        }
        
        chart = db.query(ChartImage).filter(
            ChartImage.message_id == msg.id,
            ChartImage.status == 1
        ).first()
        
        if chart:
            msg_dict["chart"] = {
                "id": chart.id,
                "symbol": chart.symbol,
                "chart_type": chart.chart_type,
                "duration_seconds": chart.duration_seconds,
                "image_base64": chart.image_base64,
                "image_format": chart.image_format,
                "data_count": chart.data_count
            }
        
        message_list.append(msg_dict)
    
    return {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat() if chat.created_at is not None else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at is not None else None,
        "total_messages": total_messages,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_messages + page_size - 1) // page_size,
        "messages": message_list
    }

@app.put("/api/chats/{chat_id}")
async def update_chat(chat_id: int, request: ChatUpdateRequest, user_id: str = 'global', db: Session = Depends(get_db)):
    print(f"=== 接收到更新对话请求 ===")
    print(f"对话ID: {chat_id}")
    print(f"用户ID: {user_id}")
    print(f"请求数据: {request}")
    
    # 只查询状态为正常的对话（软删除过滤）
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
    if not chat:
        print(f"对话 {chat_id} 未找到")
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 更新标题（如果提供）
    if request.title is not None:
        chat.title = request.title  # type: ignore
        print(f"更新标题: {request.title}")
    
    # 更新消息（如果提供）
    if request.messages is not None:
        print(f"开始更新消息，共 {len(request.messages)} 条消息")
        # 删除现有消息
        deleted_count = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).delete()
        print(f"删除了 {deleted_count} 条现有消息")
        
        # 添加新消息
        for i, msg in enumerate(request.messages):
            print(f"处理第 {i+1} 条消息: {msg}")
            message = DBMessage(
                chat_id=chat_id, 
                role=msg.get("role"), 
                content=msg.get("content"),
                details=json.dumps(msg.get("details")) if msg.get("details") else None,
                user_id=user_id
            )
            db.add(message)
            print(f"消息已添加: role={msg.get('role')}, content长度={len(msg.get('content', ''))}, details={msg.get('details')}")
        
        # 更新缓存
        conversation_cache.set(chat_id, user_id, request.messages)
        print(f"对话 {chat_id} 的消息已更新，共 {len(request.messages)} 条消息")
    
    db.commit()
    db.refresh(chat)
    print(f"数据库提交完成")
    
    return {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat() if chat.created_at is not None else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at is not None else None
    }

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: int, user_id: str = 'global', db: Session = Depends(get_db)):
    # 只查询状态为正常的对话（软删除过滤）
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 软删除：将status设置为0
    chat.status = 0  # type: ignore
    db.commit()
    
    # 从缓存中删除对话历史
    conversation_cache.delete(chat_id, user_id)
    print(f"已软删除对话 {chat_id}")
    
    return {"status": "success", "message": "Chat deleted"}

@app.post("/api/chats/{chat_id}/messages")
async def add_message(chat_id: int, request: MessageCreateRequest, user_id: str = 'global', db: Session = Depends(get_db)):
    # 只查询状态为正常的对话（软删除过滤）
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id, Chat.status == 1).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    message = DBMessage(chat_id=chat_id, role=request.role, content=request.content, user_id=request.user_id)
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # 更新缓存
    updated_messages = db.query(DBMessage).filter(DBMessage.chat_id == chat_id, DBMessage.user_id == user_id).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).all()
    updated_history = [{"role": msg.role, "content": msg.content} for msg in updated_messages]
    conversation_cache.set(chat_id, user_id, updated_history)
    print(f"对话历史缓存已更新")
    
    # 如果是用户的第一条消息，自动生成对话标题
    if request.role == 'user':
        # 检查是否是第一条消息
        message_count = db.query(DBMessage).filter(DBMessage.chat_id == chat_id).count()
        # 检查当前标题是否为"新对话"
        if message_count == 1 and str(chat.title) == "新对话":
            # 生成标题
            title = await generate_chat_title(request.content, db)
            # 更新对话标题
            chat.title = title
            db.commit()
    
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at is not None else None
    }

# API配置管理接口 - 从数据库获取所有API配置
@app.get("/api/model-configs")
async def get_model_configs(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """获取所有模型API配置（只返回模型名称）"""
    # 如果没有提供user_id，默认为'global'（全局配置）
    if user_id is None:
        user_id = 'global'
    
    # 获取用户的默认模型ID
    default_model_id = None
    if user_id != 'global':
        user = db.query(SysUser).filter(SysUser.user_id == user_id, SysUser.status == 1).first()
        if user:
            default_model_id = user.default_model_id
    
    # 获取金融助手默认模型ID
    finance_default_model_id = None
    if user_id != 'global':
        finance_config = db.query(FinanceConfig).filter(FinanceConfig.user_id == user_id, FinanceConfig.status == 1).first()
        if finance_config and finance_config.default_model_id:
            finance_default_model_id = finance_config.default_model_id
    
    # 查询用户个人配置和全局配置，过滤掉已删除的记录(status=0)
    configs = db.query(ModelConfig).filter(
        ((ModelConfig.user_id == user_id) | (ModelConfig.user_id == 'global')) &
        (ModelConfig.status == 1)
    ).order_by(ModelConfig.user_id.desc(), ModelConfig.id.asc()).all()
    
    return {
        "models": [
            {
                "id": config.id,
                "name": config.name,
                "status": config.status,
                "isGlobal": config.user_id == 'global',
                "isDefault": config.id == default_model_id,
                "isFinanceDefault": config.id == finance_default_model_id
            }
            for config in configs
        ]
    }

# API配置管理接口 - 添加新的API配置
@app.post("/api/model-configs")
async def create_model_config(request: Dict[str, Any], db: Session = Depends(get_db)):
    """添加新的模型API配置"""
    try:
        name = request.get("name")
        api_key = request.get("apiKey")
        api_url = request.get("apiUrl")
        user_id = request.get("userId", 'global')  # 默认为全局配置
        
        if not name or not api_key or not api_url:
            raise HTTPException(status_code=400, detail="缺少必要参数: name, apiKey, apiUrl")
        
        # 检查是否已存在同名配置（同一用户下），过滤掉已删除的记录
        existing = db.query(ModelConfig).filter(
            ModelConfig.user_id == user_id,
            ModelConfig.name == name,
            ModelConfig.status == 1
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"模型名称 '{name}' 已存在")
        
        config = ModelConfig(
            user_id=user_id,
            name=name,
            api_key=api_key,
            api_url=api_url,
            status=1
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return {
            "status": "success",
            "message": "API配置添加成功",
            "model": {
                "id": config.id,
                "name": config.name,
                "apiKey": config.api_key,
                "apiUrl": config.api_url,
                "status": config.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加API配置失败: {str(e)}")

# API配置管理接口 - 更新API配置
@app.put("/api/model-configs/{config_id}")
async def update_model_config(config_id: int, request: Dict[str, Any], user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """更新模型API配置"""
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="API配置不存在")
        
        # 验证权限：用户只能更新自己的模型
        # 如果提供了user_id，确保模型属于该用户
        # 类型忽略：SQLAlchemy Column 比较
        if user_id and str(config.user_id) != user_id:  # type: ignore
            raise HTTPException(status_code=403, detail="无权更新此模型配置")
        
        if "name" in request:
            config.name = request["name"]
        if "apiKey" in request:
            config.api_key = request["apiKey"]
        if "apiUrl" in request:
            config.api_url = request["apiUrl"]
        
        db.commit()
        db.refresh(config)
        
        return {
            "status": "success",
            "message": "API配置更新成功",
            "model": {
                "id": config.id,
                "name": config.name,
                "apiKey": config.api_key,
                "apiUrl": config.api_url,
                "status": config.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新API配置失败: {str(e)}")

# 系统提示词管理接口 - 获取用户的系统提示词
DEFAULT_SYSTEM_PROMPT = "你是一个教学智能体，专注于帮助学生解决学习问题，提供详细的解释和指导。"

@app.get("/api/system-prompt")
async def get_system_prompt(user_id: str, db: Session = Depends(get_db)):
    """获取用户的系统提示词"""
    try:
        user = db.query(SysUser).filter(SysUser.user_id == user_id, SysUser.status == 1).first()
        if not user:
            return {
                "system_prompt": DEFAULT_SYSTEM_PROMPT
            }
        
        system_prompt = user.system_prompt if user.system_prompt else DEFAULT_SYSTEM_PROMPT
        
        return {
            "system_prompt": system_prompt
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统提示词失败: {str(e)}")

# 系统提示词管理接口 - 更新用户的系统提示词
class SystemPromptUpdateRequest(BaseModel):
    system_prompt: str

@app.put("/api/system-prompt")
async def update_system_prompt(request: SystemPromptUpdateRequest, user_id: str, db: Session = Depends(get_db)):
    """更新用户的系统提示词"""
    try:
        system_prompt = request.system_prompt
        if not system_prompt:
            raise HTTPException(status_code=400, detail="缺少必要参数: system_prompt")
        
        # 查找用户
        user = db.query(SysUser).filter(SysUser.user_id == user_id, SysUser.status == 1).first()
        if not user:
            # 如果用户不存在，创建新用户
            user = SysUser(
                user_id=user_id,
                username=user_id,
                password_hash="",  # 密码哈希为空，因为这是系统生成的用户
                system_prompt=system_prompt
            )
            db.add(user)
        else:
            # 更新系统提示词
            user.system_prompt = system_prompt
        
        db.commit()
        db.refresh(user)
        
        return {
            "status": "success",
            "message": "系统提示词更新成功",
            "system_prompt": user.system_prompt
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新系统提示词失败: {str(e)}")

# API配置管理接口 - 删除API配置
@app.delete("/api/model-configs/{config_id}")
async def delete_model_config(config_id: int, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """删除模型API配置（软删除）"""
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="API配置不存在")
        
        # 验证权限：用户只能删除自己的模型
        # 如果提供了user_id，确保模型属于该用户
        # 类型忽略：SQLAlchemy Column 比较
        if user_id and str(config.user_id) != user_id:  # type: ignore
            raise HTTPException(status_code=403, detail="无权删除此模型配置")
        
        # 软删除：将status设置为0
        # 类型忽略：SQLAlchemy Column 赋值
        config.status = 0  # type: ignore
        db.commit()
        
        return {"status": "success", "message": "API配置删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除API配置失败: {str(e)}")

# API配置管理接口 - 设置默认模型
@app.post("/api/model-configs/{config_id}/default")
async def set_default_model(config_id: int, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """设置默认模型"""
    try:
        # 验证模型是否存在
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id, ModelConfig.status == 1).first()
        if not config:
            raise HTTPException(status_code=404, detail="API配置不存在")
        
        # 如果提供了user_id，验证模型属于该用户或者是全局配置
        if user_id:
            if str(config.user_id) != user_id and str(config.user_id) != 'global':  # type: ignore
                raise HTTPException(status_code=403, detail="无权设置此模型为默认")
            
            # 查找或创建用户记录
            user = db.query(SysUser).filter(SysUser.user_id == user_id, SysUser.status == 1).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 更新用户的默认模型ID
            user.default_model_id = config_id  # type: ignore
            db.commit()
            
            return {"status": "success", "message": "默认模型设置成功"}
        else:
            raise HTTPException(status_code=400, detail="需要提供user_id参数")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"设置默认模型失败: {str(e)}")

# 功能模型映射管理接口 - 获取所有功能模型映射
@app.get("/api/feature-model-mappings")
async def get_feature_model_mappings(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """获取所有功能模型映射"""
    # 如果没有提供user_id，默认为'global'（全局配置）
    if user_id is None:
        user_id = 'global'
    
    # 查询用户个人配置和全局配置，过滤掉已删除的记录(status=0)
    mappings = db.query(FeatureModelMapping).filter(
        ((FeatureModelMapping.user_id == user_id) | (FeatureModelMapping.user_id == 'global')) &
        (FeatureModelMapping.status == 1)
    ).order_by(FeatureModelMapping.user_id.desc(), FeatureModelMapping.id.asc()).all()
    
    return {
        "mappings": [
            {
                "id": mapping.id,
                "feature_name": mapping.feature_name,
                "model_name": mapping.model_name,
                "user_id": mapping.user_id,
                "isGlobal": mapping.user_id == 'global'
            }
            for mapping in mappings
        ]
    }

# 功能模型映射管理接口 - 更新功能模型映射
@app.post("/api/feature-model-mappings")
async def update_feature_model_mapping_api(request: Dict[str, Any], db: Session = Depends(get_db)):
    """更新功能模型映射"""
    try:
        feature_name = request.get("feature_name")
        model_name = request.get("model_name")
        user_id = request.get("user_id", 'global')  # 默认为全局配置
        
        if not feature_name or not model_name:
            raise HTTPException(status_code=400, detail="缺少必要参数: feature_name, model_name")
        
        # 验证模型是否存在
        model_config = get_model_config(model_name, user_id)
        if not model_config.get("name"):
            raise HTTPException(status_code=400, detail=f"模型 '{model_name}' 不存在")
        
        # 更新映射
        success = update_feature_model_mapping(feature_name, model_name, user_id)
        if not success:
            raise HTTPException(status_code=500, detail="更新功能模型映射失败")
        
        return {
            "status": "success",
            "message": "功能模型映射更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新功能模型映射失败: {str(e)}")

# 用户认证API
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    user_id: str
    username: str
    created_at: datetime

@app.post("/api/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        existing_user = db.query(SysUser).filter(
            SysUser.username == request.username,
            SysUser.status == 1
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 生成用户ID
        import uuid
        user_id = f"user_{uuid.uuid4()}"
        
        # 生成密码哈希
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        
        # 创建新用户
        user = SysUser(
            user_id=user_id,
            username=request.username,
            password_hash=password_hash
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {
            "status": "success",
            "message": "注册成功",
            "user": {
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "created_at": user.created_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

@app.post("/api/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        # 查找用户
        user = db.query(SysUser).filter(
            SysUser.username == request.username,
            SysUser.status == 1
        ).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 验证密码
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        if str(user.password_hash) != password_hash:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        return {
            "status": "success",
            "message": "登录成功",
            "user": {
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "created_at": user.created_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

class FinanceConfigRequest(BaseModel):
    user_id: str
    default_model_id: Optional[int] = None
    system_prompt: Optional[str] = None
    kuaiqi_account: Optional[str] = None
    kuaiqi_password: Optional[str] = None

DEFAULT_FINANCE_SYSTEM_PROMPT = "你是一个专业的金融助手，专注于提供金融分析、投资建议、市场解读等服务。请用专业但易懂的方式回答用户的问题。"

@app.get("/api/finance-config")
async def get_finance_config(user_id: str, db: Session = Depends(get_db)):
    config = db.query(FinanceConfig).filter(FinanceConfig.user_id == user_id, FinanceConfig.status == 1).first()
    if not config:
        config = FinanceConfig(user_id=user_id, system_prompt=DEFAULT_FINANCE_SYSTEM_PROMPT)
        db.add(config)
        db.commit()
        db.refresh(config)
    
    default_model_name = None
    if config.default_model_id:
        model = db.query(ModelConfig).filter(ModelConfig.id == config.default_model_id, ModelConfig.status == 1).first()
        if model:
            default_model_name = model.name
    
    system_prompt = config.system_prompt if config.system_prompt else DEFAULT_FINANCE_SYSTEM_PROMPT
    
    return {
        "id": config.id,
        "user_id": config.user_id,
        "default_model_id": config.default_model_id,
        "default_model_name": default_model_name,
        "system_prompt": system_prompt,
        "kuaiqi_account": config.kuaiqi_account,
        "has_kuaiqi_password": bool(config.kuaiqi_password),
        "created_at": config.created_at.isoformat() if config.created_at is not None else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at is not None else None
    }

@app.put("/api/finance-config")
async def update_finance_config(request: FinanceConfigRequest, db: Session = Depends(get_db)):
    config = db.query(FinanceConfig).filter(FinanceConfig.user_id == request.user_id, FinanceConfig.status == 1).first()
    if not config:
        config = FinanceConfig(user_id=request.user_id, system_prompt=DEFAULT_FINANCE_SYSTEM_PROMPT)
        db.add(config)
    
    if request.default_model_id is not None:
        config.default_model_id = request.default_model_id
    if request.system_prompt is not None:
        config.system_prompt = request.system_prompt
    if request.kuaiqi_account is not None:
        config.kuaiqi_account = request.kuaiqi_account
    if request.kuaiqi_password is not None:
        config.kuaiqi_password = request.kuaiqi_password
    
    db.commit()
    db.refresh(config)
    
    default_model_name = None
    if config.default_model_id:
        model = db.query(ModelConfig).filter(ModelConfig.id == config.default_model_id, ModelConfig.status == 1).first()
        if model:
            default_model_name = model.name
    
    return {
        "id": config.id,
        "user_id": config.user_id,
        "default_model_id": config.default_model_id,
        "default_model_name": default_model_name,
        "system_prompt": config.system_prompt,
        "kuaiqi_account": config.kuaiqi_account,
        "has_kuaiqi_password": bool(config.kuaiqi_password),
        "created_at": config.created_at.isoformat() if config.created_at is not None else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at is not None else None
    }

class FinanceDefaultModelRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: int

@app.put("/api/finance-config/default-model")
async def set_finance_default_model(user_id: str, request: FinanceDefaultModelRequest, db: Session = Depends(get_db)):
    config = db.query(FinanceConfig).filter(FinanceConfig.user_id == user_id, FinanceConfig.status == 1).first()
    if not config:
        config = FinanceConfig(user_id=user_id, default_model_id=request.model_id, system_prompt=DEFAULT_FINANCE_SYSTEM_PROMPT)
        db.add(config)
    else:
        config.default_model_id = request.model_id
    
    db.commit()
    db.refresh(config)
    
    default_model_name = None
    if config.default_model_id:
        model = db.query(ModelConfig).filter(ModelConfig.id == config.default_model_id, ModelConfig.status == 1).first()
        if model:
            default_model_name = model.name
    
    system_prompt = config.system_prompt if config.system_prompt else DEFAULT_FINANCE_SYSTEM_PROMPT
    
    return {
        "id": config.id,
        "user_id": config.user_id,
        "default_model_id": config.default_model_id,
        "default_model_name": default_model_name,
        "system_prompt": system_prompt,
        "created_at": config.created_at.isoformat() if config.created_at is not None else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at is not None else None
    }

class ToolExecuteRequest(BaseModel):
    tool_name: str
    params: dict = {}
    chat_id: Optional[int] = None
    user_id: Optional[str] = 'global'
    message_index: Optional[int] = None
    code: Optional[str] = None

@app.get("/api/tools")
async def get_tools():
    tools = []
    for name, info in TOOL_CODES.items():
        tools.append({
            "name": name,
            "display_name": info["name"],
            "description": info["description"],
            "params": info["params"]
        })
    return {"tools": tools}

@app.get("/api/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    tool = get_tool_code(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "name": tool_name,
        "display_name": tool["name"],
        "description": tool["description"],
        "code": tool["code"],
        "params": tool["params"]
    }

@app.post("/api/tools/execute/stream")
async def execute_tool_stream(request: ToolExecuteRequest, db: Session = Depends(get_db)):
    import subprocess
    import tempfile
    import os
    import json
    import asyncio
    
    tool = get_tool_code(request.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    code = request.code if request.code else tool["code"]
    
    if not code and tool.get("strategy_codes"):
        strategy = request.params.get("strategy") if request.params else None
        print(f"选择策略代码: strategy={strategy}, available_strategies={list(tool.get('strategy_codes', {}).keys())}")
        if strategy and strategy in tool["strategy_codes"]:
            code = tool["strategy_codes"][strategy]
            print(f"使用策略代码: {strategy}, code_length={len(code)}")
    
    if not code:
        print(f"错误: 代码为空! tool_name={request.tool_name}, request.code={request.code}, tool['code']={tool.get('code')}")
        async def error_stream():
            chunk_response = {
                "type": "error",
                "message": f"工具 {request.tool_name} 没有可执行的代码"
            }
            yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return error_stream()
    
    params = dict(request.params)
    if 'user_id' not in params and request.user_id:
        params['user_id'] = request.user_id
    
    params_str = ", ".join([f"{k}={repr(v)}" for k, v in params.items()])
    call_code = f'''
import json
import math

def json_serialize(obj):
    def convert(o):
        if isinstance(o, dict):
            return {{k: convert(v) for k, v in o.items()}}
        elif isinstance(o, list):
            return [convert(i) for i in o]
        elif isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return None
            return o
        return o
    return convert(obj)

_result = {request.tool_name}({params_str})
print("__RESULT_START__")
print(json.dumps(json_serialize(_result), ensure_ascii=False))
print("__RESULT_END__")
'''
    
    full_code = code + call_code
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(full_code)
        temp_file = f.name
    
    print(f"\n{'='*60}")
    print(f"临时执行文件: {temp_file}")
    print(f"{'='*60}")
    print(f"执行代码:")
    print(full_code)
    print(f"{'='*60}\n")
    
    chat_id = request.chat_id
    user_id = request.user_id
    
    async def stream_execute():
        nonlocal chat_id, user_id
        process_output = ""
        final_result = None
        result_lines = None
        process = None
        temp_file_to_delete = temp_file
        
        try:
            process = await asyncio.create_subprocess_exec(
                'python', '-u', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            
            while True:
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=120.0
                    )
                except asyncio.TimeoutError:
                    print(f"工具执行超时，正在终止进程...")
                    try:
                        process.kill()
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except:
                        try:
                            process.terminate()
                            await process.wait()
                        except:
                            pass
                    chunk_response = {
                        "type": "error",
                        "message": "执行超时（120秒）"
                    }
                    yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                if not line and process.returncode is not None:
                    break
                
                if line:
                    line = line.decode('utf-8', errors='replace').rstrip('\n\r')
                    if line == "__RESULT_START__":
                        result_lines = []
                        continue
                    elif line == "__RESULT_END__":
                        if result_lines is not None:
                            result_json = '\n'.join(result_lines)
                            try:
                                final_result = json.loads(result_json)
                            except:
                                final_result = result_json
                        break
                    elif result_lines is not None:
                        result_lines.append(line)
                    else:
                        process_output += line + '\n'
                        chunk_response = {
                            "type": "process_output",
                            "line": line
                        }
                        yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0)
            
            stderr_bytes, _ = await process.communicate()
            stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ''
            
            success = process.returncode == 0
            
            print(f"=== 工具执行完成 ===")
            print(f"success: {success}")
            print(f"final_result: {final_result}")
            print(f"process_output length: {len(process_output)}")
            print(f"stderr: {stderr}")
            
            if not success:
                error_parts = []
                if stderr.strip():
                    error_parts.append(stderr.strip())
                if process_output.strip():
                    error_parts.append(f"输出: {process_output.strip()}")
                error_msg = "\n".join(error_parts) if error_parts else "未知错误"
                chunk_response = {
                    "type": "error",
                    "message": error_msg
                }
                yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)
            
            result_content = ""
            if final_result is not None:
                result_content = f"✅ 执行结果:\n```json\n{json.dumps(final_result, ensure_ascii=False, indent=2)}\n```"
            elif not success:
                error_parts = []
                if stderr.strip():
                    error_parts.append(stderr.strip())
                if process_output.strip():
                    error_parts.append(f"输出: {process_output.strip()}")
                error_msg = "\n".join(error_parts) if error_parts else "未知错误"
                result_content = f"❌ 工具执行失败: {error_msg}"
            
            details_parts = []
            if process_output.strip():
                details_parts.append({
                    "type": "tool_execution",
                    "process": process_output.strip()
                })
            
            if chat_id:
                try:
                    from database import SessionLocal
                    db_session = SessionLocal()
                    try:
                        details_content = json.dumps(details_parts, ensure_ascii=False) if details_parts else None
                        message = DBMessage(
                            chat_id=chat_id,
                            role='assistant',
                            content=result_content,
                            details=details_content,
                            user_id=user_id
                        )
                        db_session.add(message)
                        db_session.commit()
                        
                        updated_messages = db_session.query(DBMessage).filter(
                            DBMessage.chat_id == chat_id,
                            DBMessage.user_id == user_id
                        ).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).all()
                        updated_history = [{"role": msg.role, "content": msg.content} for msg in updated_messages]
                        conversation_cache.set(chat_id, user_id, updated_history)
                    finally:
                        db_session.close()
                except Exception as e:
                    print(f"保存数据库失败: {e}")
            
            chunk_response = {
                "type": "done",
                "success": success,
                "result": final_result,
                "process_output": process_output.strip()
            }
            print(f"发送 done 消息: {chunk_response}")
            yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"流式执行错误: {e}")
            import traceback
            traceback.print_exc()
            chunk_response = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(chunk_response, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            if process and process.returncode is None:
                try:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except:
                    try:
                        process.terminate()
                        await process.wait()
                    except:
                        pass
            try:
                os.unlink(temp_file_to_delete)
            except:
                pass
    
    return StreamingResponse(
        stream_execute(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/api/tools/execute")
async def execute_tool(request: ToolExecuteRequest, db: Session = Depends(get_db)):
    import subprocess
    import tempfile
    import os
    import json
    
    tool = get_tool_code(request.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    code = tool["code"]
    
    params = dict(request.params)
    if 'user_id' not in params and request.user_id:
        params['user_id'] = request.user_id
    
    params_str = ", ".join([f"{k}={repr(v)}" for k, v in params.items()])
    call_code = f'''
import json
import math

def json_serialize(obj):
    def convert(o):
        if isinstance(o, dict):
            return {{k: convert(v) for k, v in o.items()}}
        elif isinstance(o, list):
            return [convert(i) for i in o]
        elif isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return None
            return o
        return o
    return convert(obj)

_result = {request.tool_name}({params_str})
print("__RESULT_START__")
print(json.dumps(json_serialize(_result), ensure_ascii=False))
print("__RESULT_END__")
'''
    
    full_code = code + call_code
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(full_code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ['python', '-u', temp_file],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        success = result.returncode == 0
        
        process_output = ""
        final_result = None
        
        if success and result.stdout:
            stdout = result.stdout
            if "__RESULT_START__" in stdout and "__RESULT_END__" in stdout:
                start_marker = "__RESULT_START__"
                end_marker = "__RESULT_END__"
                
                start_idx = stdout.find(start_marker)
                end_idx = stdout.find(end_marker)
                
                process_output = stdout[:start_idx].strip()
                result_json = stdout[start_idx + len(start_marker):end_idx].strip()
                
                try:
                    final_result = json.loads(result_json)
                except:
                    final_result = result_json
            else:
                process_output = stdout
        elif not success:
            process_output = result.stderr or "未知错误"
        
        result_content = ""
        if process_output:
            result_content += f"执行过程:\n{process_output}\n\n"
        if final_result is not None:
            result_content += f"执行结果:\n{json.dumps(final_result, ensure_ascii=False, indent=2)}"
        elif not success:
            result_content = f"工具执行失败: {result.stderr or '未知错误'}"
        
        if request.chat_id and result_content:
            message = DBMessage(
                chat_id=request.chat_id,
                role='assistant',
                content=result_content,
                user_id=request.user_id
            )
            db.add(message)
            db.commit()
            
            updated_messages = db.query(DBMessage).filter(
                DBMessage.chat_id == request.chat_id,
                DBMessage.user_id == request.user_id
            ).order_by(DBMessage.created_at.asc(), DBMessage.id.asc()).all()
            updated_history = [{"role": msg.role, "content": msg.content} for msg in updated_messages]
            conversation_cache.set(request.chat_id, request.user_id, updated_history)
            print(f"工具执行结果已保存到数据库")
        
        return {
            "success": success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "process_output": process_output,
            "result": final_result
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "执行超时（120秒）"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass

class GenerateChartRequest(BaseModel):
    data_type: str
    data: dict
    chart_type: Optional[str] = 'candle'
    chat_id: Optional[int] = None
    message_id: Optional[int] = None
    user_id: Optional[str] = 'global'

class GenerateChartFromMessageRequest(BaseModel):
    message_id: Optional[int] = None
    chat_id: Optional[int] = None
    message_content: Optional[str] = None
    chart_type: Optional[str] = 'candle'
    user_id: Optional[str] = 'global'

@app.post("/api/charts/generate-from-message")
async def generate_chart_from_message(request: GenerateChartFromMessageRequest, db: Session = Depends(get_db)):
    import re
    
    try:
        content = None
        
        if request.message_id:
            message = db.query(DBMessage).filter(
                DBMessage.id == request.message_id,
                DBMessage.user_id == request.user_id
            ).first()
            
            if not message:
                raise HTTPException(status_code=404, detail="消息不存在")
            
            content = message.content or ""
            chat_id = request.chat_id or message.chat_id
        elif request.message_content:
            content = request.message_content
            chat_id = request.chat_id
        else:
            raise HTTPException(status_code=400, detail="需要提供 message_id 或 message_content")
        
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, content)
        
        if not match:
            raise HTTPException(status_code=400, detail="消息中未找到JSON数据")
        
        try:
            data = json.loads(match.group(1).strip())
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"解析JSON数据失败: {str(e)}")
        
        if "error" in data:
            raise HTTPException(status_code=400, detail=f"工具执行结果包含错误: {data['error']}")
        
        data_type = None
        if data.get("klines") and isinstance(data["klines"], list) and len(data["klines"]) > 0:
            data_type = "kline"
        elif data.get("ticks") and isinstance(data["ticks"], list) and len(data["ticks"]) > 0:
            data_type = "tick"
        
        if not data_type:
            raise HTTPException(status_code=400, detail="未找到K线或Tick数据")
        
        if data_type == 'kline':
            result = generate_kline_chart(data, request.chart_type or 'candle', request.user_id)
        else:
            result = generate_tick_chart(data, request.user_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        chart_image = ChartImage(
            user_id=request.user_id,
            chat_id=chat_id,
            message_id=request.message_id,
            symbol=result.get("symbol", "Unknown"),
            chart_type=result.get("chart_type", data_type),
            duration_seconds=result.get("duration_seconds"),
            image_base64=result["image_base64"],
            image_format=result.get("image_format", "png"),
            data_count=result.get("data_count", 0),
        )
        db.add(chart_image)
        db.commit()
        db.refresh(chart_image)
        
        return {
            "success": True,
            "chart_id": chart_image.id,
            "symbol": result.get("symbol"),
            "chart_type": result.get("chart_type"),
            "duration_seconds": result.get("duration_seconds"),
            "data_count": result.get("data_count"),
            "image_base64": result["image_base64"],
            "image_format": result.get("image_format", "png"),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成图表失败: {str(e)}")

@app.post("/api/charts/generate")
async def generate_chart(request: GenerateChartRequest, db: Session = Depends(get_db)):
    try:
        data_type = request.data_type
        data = request.data
        
        if data_type == 'kline':
            result = generate_kline_chart(data, request.chart_type or 'candle', request.user_id)
        elif data_type == 'tick':
            result = generate_tick_chart(data, request.user_id)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的数据类型: {data_type}")
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        chart_image = ChartImage(
            user_id=request.user_id,
            chat_id=request.chat_id,
            message_id=request.message_id,
            symbol=result.get("symbol", "Unknown"),
            chart_type=result.get("chart_type", data_type),
            duration_seconds=result.get("duration_seconds"),
            image_base64=result["image_base64"],
            image_format=result.get("image_format", "png"),
            data_count=result.get("data_count", 0),
        )
        db.add(chart_image)
        db.commit()
        db.refresh(chart_image)
        
        return {
            "success": True,
            "chart_id": chart_image.id,
            "symbol": result.get("symbol"),
            "chart_type": result.get("chart_type"),
            "duration_seconds": result.get("duration_seconds"),
            "data_count": result.get("data_count"),
            "image_base64": result["image_base64"],
            "image_format": result.get("image_format", "png"),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成图表失败: {str(e)}")

@app.get("/api/charts/{chart_id}")
async def get_chart(chart_id: int, user_id: str = 'global', db: Session = Depends(get_db)):
    chart = db.query(ChartImage).filter(
        ChartImage.id == chart_id,
        ChartImage.user_id == user_id,
        ChartImage.status == 1
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    
    return {
        "id": chart.id,
        "user_id": chart.user_id,
        "chat_id": chart.chat_id,
        "message_id": chart.message_id,
        "symbol": chart.symbol,
        "chart_type": chart.chart_type,
        "duration_seconds": chart.duration_seconds,
        "image_base64": chart.image_base64,
        "image_format": chart.image_format,
        "data_count": chart.data_count,
        "created_at": chart.created_at.isoformat() if chart.created_at else None,
    }

@app.get("/api/charts")
async def list_charts(user_id: str, chat_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(ChartImage).filter(
        ChartImage.user_id == user_id,
        ChartImage.status == 1
    )
    
    if chat_id:
        query = query.filter(ChartImage.chat_id == chat_id)
    
    charts = query.order_by(ChartImage.created_at.desc()).limit(50).all()
    
    return {
        "charts": [
            {
                "id": c.id,
                "symbol": c.symbol,
                "chart_type": c.chart_type,
                "duration_seconds": c.duration_seconds,
                "data_count": c.data_count,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in charts
        ]
    }

@app.delete("/api/charts/{chart_id}")
async def delete_chart(chart_id: int, user_id: str, db: Session = Depends(get_db)):
    chart = db.query(ChartImage).filter(
        ChartImage.id == chart_id,
        ChartImage.user_id == user_id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    
    chart.status = 0
    db.commit()
    
    return {"success": True, "message": "图表已删除"}

if __name__ == "__main__":
    import uvicorn
    print("Starting server...")
    print("Database URL:", str(settings.DATABASE_URL) if settings.DATABASE_URL else "Not set")
    print("Trying to initialize database...")
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
    print("Starting uvicorn server...")
    uvicorn.run(app, host="127.0.0.1", port=8888, log_level="info")