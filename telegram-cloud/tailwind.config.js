/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./static/js/**/*.js"
    ],
    theme: {
        extend: {
            colors: {
                ag: {
                    cyan: {
                        50: 'hsl(190, 85%, 97%)',
                        100: 'hsl(190, 80%, 92%)',
                        400: 'hsl(190, 75%, 55%)',
                        500: 'hsl(190, 72%, 50%)',
                        600: 'hsl(190, 70%, 45%)',
                        800: 'hsl(190, 65%, 25%)',
                    },
                    violet: {
                        400: 'hsl(260, 75%, 65%)',
                        500: 'hsl(260, 72%, 60%)',
                        600: 'hsl(260, 70%, 55%)',
                        800: 'hsl(260, 65%, 35%)',
                    },
                    blue: {
                        400: 'hsl(215, 80%, 60%)',
                        500: 'hsl(215, 77%, 55%)',
                        600: 'hsl(215, 75%, 50%)',
                        800: 'hsl(215, 70%, 30%)',
                    }
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['JetBrains Mono', 'Consolas', 'monospace']
            },
            animation: {
                'shimmer': 'shimmer 2s infinite linear',
                'float': 'float 6s ease-in-out infinite',
                'spin-slow': 'spin 3s linear infinite',
            },
            keyframes: {
                shimmer: {
                    '0%': { transform: 'translateX(-100%)' },
                    '100%': { transform: 'translateX(100%)' }
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-10px)' }
                }
            },
            backdropBlur: {
                xs: '2px',
            }
        }
    },
    plugins: []
}
