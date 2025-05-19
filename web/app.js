// 邮箱验证正则
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

document.getElementById('subscribeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const emailError = document.getElementById('emailError');
    
    // 邮箱验证
    if (!emailRegex.test(email)) {
        emailError.textContent = '请输入有效的邮箱地址';
        return;
    } else {
        emailError.textContent = '';
    }
    
    try {
        // 调用后端订阅接口
        const response = await fetch('http://127.0.0.1:5000/api/subscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 跳转到支付页面
            window.location.href = data.payment_url;
        } else {
            document.getElementById('paymentStatus').textContent = 
                `错误: ${data.message || '订阅失败'}`;
        }
    } catch (error) {
        document.getElementById('paymentStatus').textContent = 
            '网络错误，请稍后再试';
    }
});

// 检查URL参数，显示支付结果
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const paymentStatus = urlParams.get('payment_status');
    
    if (paymentStatus === 'success') {
        document.getElementById('paymentStatus').textContent = 
            '订阅成功！您将开始接收OA系统通知';
    } else if (paymentStatus === 'failed') {
        document.getElementById('paymentStatus').textContent = 
            '支付失败，请重试或联系客服';
    }
});