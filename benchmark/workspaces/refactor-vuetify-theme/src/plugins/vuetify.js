import { createVuetify } from 'vuetify'

const customTheme = {
  light: {
    dark: false,
    colors: {
      primary: '#1976D2',
      secondary: '#424242',
      accent: '#82B1FF',
      error: '#FF5252',
    }
  },
  dark: {
    dark: true,
    colors: {
        primary: '#1976D2',
        secondary: '#424242',
        accent: '#82B1FF',
        error: '#FF5252',
        background: '#121212',
        surface: '#1E1E1E'
      }
  }
}

export default createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: customTheme
  }
})
