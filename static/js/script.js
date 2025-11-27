// Flash 메시지 3초 뒤 자동 삭제
document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = 0;
            setTimeout(() => alert.remove(), 500);
        }, 3000);
    });
});

// 뒤로가기 버튼 기능
function goBack() {
    window.history.back();
}