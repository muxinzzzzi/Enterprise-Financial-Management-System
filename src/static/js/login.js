const loginForm = document.getElementById('login-form');

loginForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value.trim();
  try {
    const resp = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '登录失败');
    window.location.href = '/dashboard';
  } catch (error) {
    alert(error.message || error);
  }
});
