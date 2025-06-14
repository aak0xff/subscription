import { createClient } from 'https://cdn.skypack.dev/@supabase/supabase-js'

const supabase = createClient('https://你的supabase網址.supabase.co', 'public-anon-key')

async function signInWithEmail(email) {
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: 'https://pinggle.me/auth/callback'
    }
  })
  if (error) alert("登入失敗: " + error.message)
  else alert("已寄出登入連結，請查收您的信箱")
}