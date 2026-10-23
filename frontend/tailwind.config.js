/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DocuVerify AI Professional Fintech Color Palette
        brand: {
          navy: '#14213D',
          blue: '#3478F6',
          teal: '#0F9D8A',
          violet: '#7656D6',
        },
        navy: {
          DEFAULT: '#14213D',
          950: '#0A0F1D',
          900: '#101A30',
          800: '#14213D', // Deep Navy Brand: #14213D
          700: '#1C2E54',
          600: '#253B6D',
        },
        indigo: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1',
          600: '#4F46E5', // Primary Actions & Selected Navigation: #4F46E5
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
        },
        teal: {
          50: '#E6F7F5',
          100: '#CCF0EB',
          200: '#99E1D7',
          300: '#5CD0C0',
          400: '#22BCA8',
          500: '#0F9D8A', // Successful Verification & Completed: #0F9D8A
          600: '#0D8675',
          700: '#0B6D5F',
          800: '#085349',
        },
        blue: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3478F6', // Primary Reviewer Blue: #3478F6
          600: '#2563EB',
          700: '#1D4ED8',
        },
        violet: {
          50: '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#7656D6', // Primary Approver Violet: #7656D6
          600: '#6845C9',
          700: '#5A36BC',
        },
        amber: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          200: '#FDE68A',
          300: '#FCD34D',
          400: '#FBBF24',
          500: '#D97706', // Pending Items & Warnings: #D97706
          600: '#B45309',
          700: '#92400E',
        },
        red: {
          50: '#FEF2F2',
          100: '#FEE2E2',
          200: '#FECACA',
          300: '#FCA5A5',
          400: '#F87171',
          500: '#DC4545', // Errors & Discrepancies: #DC4545
          600: '#B91C1C',
        },
        surface: {
          DEFAULT: '#F5F7FB', // Light Canvas Background
          card: '#FFFFFF',
          muted: '#EDF1F7',
          subtle: '#FAFBFD',
          border: '#E2E8F0', // Card and divider borders: #E2E8F0
        },
        main: '#1E293B', // Main Text: #1E293B
        muted: '#64748B', // Secondary Text: #64748B
        error: '#DC4545',
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgba(23,37,84,0.03)',
        sm: '0 1px 3px 0 rgba(23,37,84,0.05), 0 1px 2px -1px rgba(23,37,84,0.03)',
        card: '0 1px 3px 0 rgba(23,37,84,0.04), 0 1px 2px -1px rgba(23,37,84,0.02)',
        'card-hover': '0 6px 16px -2px rgba(23,37,84,0.07), 0 2px 6px -1px rgba(23,37,84,0.03)',
        panel: '0 10px 25px -5px rgba(23,37,84,0.08)',
      },
    },
  },
  plugins: [],
}
