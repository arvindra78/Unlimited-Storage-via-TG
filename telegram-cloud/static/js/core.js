// Core utility functions

function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const bgClass = type === 'success' ? 'bg-emerald-500' :
        type === 'error' ? 'bg-red-500' : 'bg-blue-500';

    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-xl shadow-lg text-white font-medium z-50 ${bgClass}`;
    toast.textContent = message;
    toast.style.animation = 'slideUp 0.3s ease-out';

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(1rem)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Auto-hide flash messages
document.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.getElementById('flashMessages');
    if (flashMessages) {
        setTimeout(() => {
            flashMessages.style.opacity = '0';
            flashMessages.style.transition = 'opacity 0.3s';
            setTimeout(() => flashMessages.remove(), 300);
        }, 5000);
    }
});
