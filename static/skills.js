
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.update-skill-form input[type="radio"]').forEach(input => {
        input.addEventListener('change', function() {
            const form = this.closest('.update-skill-form');
            const skillItem = form.closest('.skill-item');
            const skillId = skillItem.getAttribute('data-skill-id');
            const level = this.value;
            const csrfToken = form.csrf_token.value;

            fetch('/set_skill', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify({skill_id: skillId, level: level})
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Success:', data);
                if (level == 0) {
                    skillItem.querySelector('.skill-level').textContent = 'N/A';
                } else {
                    skillItem.querySelector('.skill-level').textContent = level;
                }
            })
            .catch((error) => {
                console.error('Error:', error);
            });
        });
    });
});
