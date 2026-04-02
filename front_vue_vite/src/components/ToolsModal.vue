<template>
    <div class="modal" @click.self="$emit('close')">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">工具选择</h3>
                <button class="close-btn" @click="$emit('close')" title="关闭">×</button>
            </div>
            <div class="tools-list">
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.web_search" id="webSearch" name="webSearch" />
                    <span>网络搜索</span>
                </label>
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.web_extractor" id="webExtractor" name="webExtractor" />
                    <span>网页提取</span>
                </label>
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.code_interpreter" id="codeInterpreter" name="codeInterpreter" />
                    <span>代码解释器</span>
                </label>
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.web_search_image" id="webSearchImage" name="webSearchImage" />
                    <span>图片搜索</span>
                </label>
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.image_search" id="imageSearch" name="imageSearch" />
                    <span>图片识别</span>
                </label>
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.file_search" id="fileSearch" name="fileSearch" />
                    <span>文件搜索</span>
                </label>
                <label class="tool-item">
                    <input type="checkbox" v-model="localTools.mcp" id="mcp" name="mcp" />
                    <span>多模态</span>
                </label>
            </div>
            <div class="modal-buttons">
                <button class="cancel-btn" @click="$emit('close')">取消</button>
                <button class="save-btn" @click="handleSave">保存</button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
    selectedTools: {
        type: Object,
        default: () => ({})
    }
});

const emit = defineEmits(['close', 'save']);

const localTools = ref({ ...props.selectedTools });

watch(() => props.selectedTools, (newTools) => {
    localTools.value = { ...newTools };
}, { deep: true });

const handleSave = () => {
    emit('save', localTools.value);
    emit('close');
};
</script>

<style scoped>
.tools-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
}

.tool-item {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    padding: 8px;
    border-radius: 6px;
    transition: background-color 0.3s ease;
}

.tool-item:hover {
    background-color: rgba(56, 189, 248, 0.1);
}

.tool-item input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
}

.tool-item span {
    font-size: 14px;
    color: #f8fafc;
}
</style>