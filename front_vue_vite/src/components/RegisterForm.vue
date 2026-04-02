<template>
    <div class="auth-container">
        <div class="auth-form">
            <h2 class="auth-title">注册</h2>
            <div v-if="error" class="auth-error">{{ error }}</div>
            <div class="auth-input-group">
                <label>用户名</label>
                <input v-model="username" type="text" placeholder="请输入用户名" id="username" name="username" />
            </div>
            <div class="auth-input-group">
                <label>密码</label>
                <input v-model="password" type="password" placeholder="请输入密码" id="password" name="password" />
            </div>
            <div class="auth-input-group">
                <label>确认密码</label>
                <input v-model="confirmPassword" type="password" placeholder="请再次输入密码" id="confirmPassword" name="confirmPassword" />
            </div>
            <button class="auth-button" @click="handleRegister">注册</button>
            <div class="auth-switch">
                已有账号？<a @click="$emit('show-login')">立即登录</a>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['register', 'show-login']);
const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const error = ref('');

const handleRegister = async () => {
    error.value = '';
    
    if (!username.value || !password.value || !confirmPassword.value) {
        error.value = '请填写完整的注册信息';
        return;
    }

    if (password.value !== confirmPassword.value) {
        error.value = '两次输入的密码不一致';
        return;
    }

    if (password.value.length < 6) {
        error.value = '密码长度至少为6位';
        return;
    }

    try {
        const response = await fetch('http://localhost:8888/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                username: username.value,
                password: password.value
            })
        });

        if (response.ok) {
            const user = await response.json();
            localStorage.setItem('agent_user_data', JSON.stringify(user));
            emit('register', user);
        } else {
            const errorData = await response.json();
            error.value = errorData.detail || '注册失败';
        }
    } catch (err) {
        error.value = '注册失败，请检查网络连接';
        console.error('注册错误:', err);
    }
};
</script>