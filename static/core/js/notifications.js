function checkNotifications() {
    fetch('/notifications/api/', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        const badge = document.getElementById('notification-badge');
        if (data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    });
}

// Check notifications every 30 seconds
setInterval(checkNotifications, 30000);
// Initial check
document.addEventListener('DOMContentLoaded', checkNotifications); 