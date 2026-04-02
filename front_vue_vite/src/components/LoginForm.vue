<template>
    <div class="auth-container">
        <div class="auth-form">
            <h2 class="auth-title">登录</h2>
            <div v-if="error" class="auth-error">{{ error }}</div>
            <div class="auth-input-group">
                <label>用户名</label>
                <input v-model="username" type="text" placeholder="请输入用户名" id="username" name="username" />
            </div>
            <div class="auth-input-group">
                <label>密码</label>
                <input v-model="password" type="password" placeholder="请输入密码" id="password" name="password" />
            </div>
            <button class="auth-button" @click="handleLogin">登录</button>
            <div class="auth-switch">
                还没有账号？<a @click="$emit('show-register')">立即注册</a>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['login', 'show-register']);
const username = ref('');
const password = ref('');
const error = ref('');

const handleLogin = async () => {
    error.value = '';
    
    if (!username.value || !password.value) {
        error.value = '请填写完整的用户名和密码';
        return;
    }

    try {
        const response = await fetch('http://localhost:8888/api/auth/login', {
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
            const data = await response.json();
            const user = data.user;
            localStorage.setItem('agent_user_data', JSON.stringify(user));
            emit('login', user);
        } else {
            const errorData = await response.json();
            error.value = errorData.detail || '登录失败';
        }
    } catch (err) {
        error.value = '登录失败，请检查网络连接';
        console.error('登录错误:', err);
    }
};
</script>