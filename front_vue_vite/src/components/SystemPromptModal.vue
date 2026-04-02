<template>
    <div class="modal" @click.self="$emit('close')">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">系统提示词</h3>
                <button class="close-btn" @click="$emit('close')" title="关闭">×</button>
            </div>
            <textarea 
                v-model="localPrompt" 
                class="system-prompt-textarea" 
                placeholder="输入系统提示词..."
                id="systemPrompt"
                name="systemPrompt"
            ></textarea>
            <div class="modal-buttons">
                <button class="cancel-btn" @click="$emit('close')">取消</button>
                <button class="save-btn" @click="handleSave">保存</button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
    systemPrompt: {
        type: String,
        default: ''
    }
});

const emit = defineEmits(['close', 'save']);

const localPrompt = ref(props.systemPrompt);

const handleSave = () => {
    emit('save', localPrompt.value);
    emit('close');
};
</script>