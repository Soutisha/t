import { useState } from 'react'
import { ShieldCheck, Smartphone, ArrowRight, LoaderCircle, UserPlus, LogIn } from 'lucide-react'
import { apiRequest, saveSession, type AuthSession } from './api'

type Props = { onAuthenticated: (session: AuthSession) => void }
type Registration = {
  display_name: string; shop_name: string; shop_type: string; address_text: string
  city: string; state: string; experience_years: string; languages: string
  service_categories: string; participation_type: string
}

const initialRegistration: Registration = {
  display_name: '', shop_name: '', shop_type: 'tyre_shop', address_text: '',
  city: '', state: '', experience_years: '0', languages: 'English',
  service_categories: 'tyres', participation_type: 'interested',
}

export default function AuthScreen({ onAuthenticated }: Props) {
  const [phone, setPhone] = useState('+91')
  const [code, setCode] = useState('')
  const [challenge, setChallenge] = useState('')
  const [devCode, setDevCode] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [registrationReady, setRegistrationReady] = useState(false)
  const [registration, setRegistration] = useState<Registration>(initialRegistration)

  async function requestCode() {
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await apiRequest<{ data: { challenge_id: string; expires_in: number; delivery: string; development_otp?: string } }>(
        '/auth/otp/request', { method: 'POST', body: JSON.stringify({ phone_e164: phone }) }, false,
      )
      setChallenge(result.data.challenge_id)
      setDevCode(result.data.development_otp || '')
      setMessage(result.data.development_otp
        ? 'Development OTP generated. This code is visible only in local development.'
        : 'OTP sent through the configured SMS provider.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not request OTP.') }
    finally { setBusy(false) }
  }

  async function verifyCode() {
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await apiRequest<{ data: AuthSession }>(
        '/auth/otp/verify', { method: 'POST', body: JSON.stringify({ phone_e164: phone, code }) }, false,
      )
      saveSession(result.data)
      onAuthenticated(result.data)
    } catch (e) {
      const text = e instanceof Error ? e.message : 'OTP verification failed.'
      if (registering && text.toLowerCase().includes('no account found')) {
        setRegistrationReady(true)
        setMessage('Mobile number verified. Complete the mechanic profile to create your account.')
      } else setError(text)
    } finally { setBusy(false) }
  }

  async function submitRegistration() {
    setBusy(true); setError(''); setMessage('')
    try {
      const payload = {
        phone_e164: phone,
        display_name: registration.display_name,
        shop_name: registration.shop_name,
        shop_type: registration.shop_type,
        address_text: registration.address_text,
        city: registration.city,
        state: registration.state,
        experience_years: Number(registration.experience_years),
        languages: registration.languages.split(',').map(x => x.trim()).filter(Boolean),
        service_categories: registration.service_categories.split(',').map(x => x.trim()).filter(Boolean),
        participation_type: registration.participation_type,
        location_consent: false,
        consent_policy_version: '1.0',
      }
      const result = await apiRequest<{ data: { message: string } }>(
        '/onboarding/mechanics', { method: 'POST', body: JSON.stringify(payload) }, false,
      )
      setRegistering(false); setRegistrationReady(false); setChallenge(''); setCode(''); setDevCode('')
      setRegistration(initialRegistration)
      setMessage(`${result.data.message} Sign in with your mobile number to continue.`)
    } catch (e) { setError(e instanceof Error ? e.message : 'Registration failed.') }
    finally { setBusy(false) }
  }

  function updateField<K extends keyof Registration>(key: K, value: Registration[K]) {
    setRegistration(current => ({ ...current, [key]: value }))
  }

  return <main className="auth-shell">
    <section className="auth-card auth-card-wide">
      <div className="auth-brand"><div className="auth-mark">e</div><div><strong>EUROGRIP</strong><small>PITSTOP OS</small></div></div>
      <div className="auth-icon"><ShieldCheck size={24}/></div>
      <span className="eyebrow">SECURE WORKSPACE ACCESS</span>
      <h1>{registrationReady ? 'Create mechanic profile' : registering ? 'Join the mechanic network' : 'Sign in to Pitstop OS'}</h1>
      <p className="auth-description">Sign in using your registered mobile number. Access is granted according to roles assigned by the platform administrator.</p>
      <div className="auth-mode">
        <button className={!registering ? 'selected' : ''} onClick={() => { setRegistering(false); setRegistrationReady(false); setChallenge(''); setCode(''); setError(''); setMessage('') }}><LogIn size={14}/> Sign in</button>
        <button className={registering ? 'selected' : ''} onClick={() => { setRegistering(true); setRegistrationReady(false); setChallenge(''); setCode(''); setError(''); setMessage('') }}><UserPlus size={14}/> Register mechanic</button>
      </div>
      {!registrationReady && <>
        <label className="auth-label">Mobile number (E.164)</label>
        <div className="auth-input"><Smartphone size={17}/><input value={phone} onChange={e => setPhone(e.target.value)} placeholder="+919876543210" autoComplete="tel"/></div>
        {!challenge ? <button className="button primary auth-submit" disabled={busy || phone.length < 8} onClick={requestCode}>{busy ? <LoaderCircle className="spin" size={16}/> : null} Send one-time password <ArrowRight size={16}/></button> :
        <>
          <label className="auth-label">6-digit OTP</label>
          <input className="auth-code" value={code} onChange={e => setCode(e.target.value.replace(/\D/g,'').slice(0,6))} inputMode="numeric" autoComplete="one-time-code" placeholder="••••••"/>
          {devCode && <div className="dev-code">Local development OTP: <b>{devCode}</b></div>}
          <button className="button primary auth-submit" disabled={busy || code.length !== 6} onClick={verifyCode}>{busy ? <LoaderCircle className="spin" size={16}/> : null} {registering ? 'Verify mobile number' : 'Verify and sign in'} <ArrowRight size={16}/></button>
          <button className="auth-resend" disabled={busy} onClick={() => { setChallenge(''); setCode(''); setDevCode('') }}>Request a new OTP</button>
        </>}
      </>}
      {registrationReady && <div className="registration-form">
        <div className="registration-grid">
          <label>Full name<input value={registration.display_name} onChange={e=>updateField('display_name',e.target.value)} placeholder="Your name"/></label>
          <label>Workshop name<input value={registration.shop_name} onChange={e=>updateField('shop_name',e.target.value)} placeholder="Workshop name"/></label>
          <label>Workshop type<select value={registration.shop_type} onChange={e=>updateField('shop_type',e.target.value)}><option value="tyre_shop">Tyre shop</option><option value="multi_brand_garage">Multi-brand garage</option><option value="puncture_shop">Puncture shop</option><option value="dealer">Dealer</option></select></label>
          <label>Experience (years)<input type="number" min="0" max="70" value={registration.experience_years} onChange={e=>updateField('experience_years',e.target.value)}/></label>
          <label className="span-two">Workshop address<textarea value={registration.address_text} onChange={e=>updateField('address_text',e.target.value)} placeholder="Street, locality and landmark"/></label>
          <label>City<input value={registration.city} onChange={e=>updateField('city',e.target.value)} placeholder="City"/></label>
          <label>State<input value={registration.state} onChange={e=>updateField('state',e.target.value)} placeholder="State"/></label>
          <label>Languages (comma separated)<input value={registration.languages} onChange={e=>updateField('languages',e.target.value)} /></label>
          <label>Service categories<input value={registration.service_categories} onChange={e=>updateField('service_categories',e.target.value)} /></label>
          <label className="span-two">Participation type<select value={registration.participation_type} onChange={e=>updateField('participation_type',e.target.value)}><option value="interested">Interested</option><option value="stockist">Stockist</option><option value="non_stockist_advocate">Non-stockist advocate</option><option value="training_participant">Training participant</option></select></label>
        </div>
        <p className="registration-consent">Location sharing is disabled by default. You can manage optional privacy consents after registration.</p>
        <button className="button primary auth-submit" disabled={busy || !registration.display_name.trim() || !registration.shop_name.trim() || registration.address_text.trim().length < 5 || !registration.city.trim() || !registration.state.trim()} onClick={submitRegistration}>{busy ? <LoaderCircle className="spin" size={16}/> : null} Create mechanic account <ArrowRight size={16}/></button>
      </div>}
      {message && <div className="auth-message">{message}</div>}
      {error && <div className="auth-error">{error}</div>}
      <div className="auth-foot">Protected by OTP verification and server-side role-based access control. Administrator privileges are assigned separately by an authorised operator.</div>
    </section>
  </main>
}
