import { useEffect, useMemo, useState } from 'react'
import { apiRequest } from './api'
import { RefreshCw, Plus, ShieldCheck, BookOpen, MapPin, Bot, CheckCircle2 } from 'lucide-react'

type Json = Record<string, any>
type Props = { title: string; role: string; notify: (message: string) => void }

const configs: Record<string, { endpoints: { label: string; path: string; admin?: boolean }[]; description: string }> = {
  'My Dashboard': { description: 'A personal view of your professional profile, learning, advocacy activity and earned rewards.', endpoints: [{label:'My Passport',path:'/passport/me'},{label:'My rewards',path:'/rewards/me'},{label:'My learning',path:'/academy/my-learning'},{label:'My advocacy events',path:'/advocacy/me/events'},{label:'My evidence',path:'/trustvision/me/evidence'}] },
  'Mechanic Passport': { description: 'Your verified professional profile, skills, progression and public visibility controls.', endpoints: [{label:'My Passport',path:'/passport/me'},{label:'Pending skills (admin)',path:'/admin/passport/skills/pending',admin:true}] },
  'Smart Tool Bank': { description: 'Browse available equipment, submit requests and review your reward balance.', endpoints: [{label:'Tool catalogue',path:'/toolbank/catalog'},{label:'My requests',path:'/toolbank/requests/me'},{label:'My rewards',path:'/rewards/me'},{label:'Pending requests (admin)',path:'/admin/toolbank/requests/pending',admin:true},{label:'Pending redemptions (admin)',path:'/admin/rewards/redemptions/pending',admin:true}] },
  'Rewards & recognition': { description: 'View your reward ledger and request a redemption.', endpoints: [{label:'My rewards',path:'/rewards/me'},{label:'Pending redemptions (admin)',path:'/admin/rewards/redemptions/pending',admin:true}] },
  'Advocacy intelligence': { description: 'Submit product recommendations and fitment records. These remain separate verified outcomes.', endpoints: [{label:'Product catalogue',path:'/advocacy/products'},{label:'My advocacy events',path:'/advocacy/me/events'},{label:'Campaigns',path:'/advocacy/campaigns'},{label:'Review queue (admin)',path:'/admin/advocacy/review-queue',admin:true}] },
  'Product catalogue': { description: 'Explore the current product records. Fitment must be supported by authorised product documentation.', endpoints: [{label:'Products',path:'/advocacy/products'},{label:'Review queue (admin)',path:'/admin/advocacy/review-queue',admin:true}] },
  'Training academy': { description: 'Browse published learning content, enrol, track lessons and review certificates.', endpoints: [{label:'Published courses',path:'/academy/courses'},{label:'My learning',path:'/academy/my-learning'},{label:'My certificates',path:'/academy/certificates/me'},{label:'All courses (admin)',path:'/admin/academy/courses',admin:true}] },
  'Territory intelligence': { description: 'Manage your saved location and discover only locations whose owners explicitly opted in.', endpoints: [{label:'My locations',path:'/geo/locations/me'}] },
  'TrustVision review': { description: 'Submit image evidence or, for authorised reviewers, inspect risk signals and make human review decisions.', endpoints: [{label:'My evidence',path:'/trustvision/me/evidence'},{label:'Review queue',path:'/admin/trustvision/review-queue',admin:true}] },
  'AI Copilot': { description: 'Ask the approved knowledge base and run read-only agent workflows. Unsupported questions are deliberately declined.', endpoints: [{label:'Knowledge documents (admin)',path:'/admin/copilot/documents',admin:true}] },
  'Privacy & data': { description: 'Review your consent records and request account deletion. Deletion requests require administrator review and an explicit execution step.', endpoints: [{label:'My consent records',path:'/me/privacy/consents'},{label:'My deletion requests',path:'/me/privacy/deletion-requests'},{label:'Deletion requests (admin)',path:'/admin/privacy/deletion-requests',admin:true}] },
}

function pretty(value: any) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function Records({ title, value, onAction }: { title: string; value: any; onAction?: (row: Json, section: string) => void }) {
  const rows = Array.isArray(value) ? value : value && typeof value === 'object' ? [value] : []
  if (!rows.length) return <div className="module-empty">No records returned for this view.</div>
  const keys = Array.from(new Set(rows.flatMap((r: Json) => Object.keys(r || {})))).slice(0, 8)
  if (!Array.isArray(value) && value && typeof value === 'object' && Object.values(value).some(Array.isArray)) {
    return <section className="panel module-records"><div className="panel-head"><div><h2>{title}</h2><p>Review queues grouped by record type</p></div></div>
      {Object.entries(value).map(([group,items]) => Array.isArray(items) ? <Records key={group} title={group.replace(/_/g,' ')} value={items} onAction={onAction}/> : null)}
    </section>
  }
  return <section className="panel module-records">
    <div className="panel-head"><div><h2>{title}</h2><p>{rows.length} record{rows.length === 1 ? '' : 's'} returned by the API</p></div></div>
    <div className="module-record-grid">{rows.map((row: Json, i: number) => <article className="module-record" key={row.id || row.product_id || row.course_id || row.enrollment_id || row.case_id || i}>
      <div className="module-record-title">{pretty(row.name || row.title || row.product_name || row.course?.title || row.reward_name || row.display_name || row.mechanic_code || row.case_type || row.filename || `Record ${i+1}`)}</div>
      {keys.filter(k => !['name','title','product_name','course','reward_name','display_name'].includes(k)).slice(0,6).map(k => <div className="module-field" key={k}><span>{k.replace(/_/g,' ')}</span><b>{pretty(row[k])}</b></div>)}
      {onAction && <button className="button secondary compact" onClick={() => onAction(row,title)}>Select record</button>}
    </article>)}</div>
  </section>
}

export default function WorkspaceModules({ title, role, notify }: Props) {
  const config = configs[title]
  const [datasets, setDatasets] = useState<Record<string, any>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<any>(null)
  const [selected, setSelected] = useState<Json | null>(null)
  const [question, setQuestion] = useState('')
  const [skill, setSkill] = useState('')
  const [years, setYears] = useState('0')
  const [reason, setReason] = useState('')
  const [rewardName, setRewardName] = useState('')
  const [points, setPoints] = useState('100')
  const [recommendNotes, setRecommendNotes] = useState('')
  const [vehicle, setVehicle] = useState('')
  const [locationName, setLocationName] = useState('')
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [consent, setConsent] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [evidenceKind, setEvidenceKind] = useState('invoice')
  const [newSku,setNewSku]=useState('')
  const [newProductName,setNewProductName]=useState('')
  const [newProductType,setNewProductType]=useState('')
  const [initialQuantity,setInitialQuantity]=useState('0')
  const [knowledgeTitle,setKnowledgeTitle]=useState('')
  const [knowledgeCategory,setKnowledgeCategory]=useState('general')
  const [knowledgeFile,setKnowledgeFile]=useState<File|null>(null)
  const [nearbyRadius,setNearbyRadius]=useState('10')
  const [nearbyResults,setNearbyResults]=useState<any[]>([])
  const [courseCode,setCourseCode]=useState('')
  const [courseTitle,setCourseTitle]=useState('')
  const [lessonTitle,setLessonTitle]=useState('')
  const [lessonContent,setLessonContent]=useState('')
  const [quizPrompt,setQuizPrompt]=useState('')
  const [quizOptions,setQuizOptions]=useState('Option A,Option B')
  const [correctOption,setCorrectOption]=useState('0')
  const [quizAnswers,setQuizAnswers]=useState<Record<string,number>>({})
  const [campaignCode,setCampaignCode]=useState('')
  const [campaignTitle,setCampaignTitle]=useState('')
  const [campaignStart,setCampaignStart]=useState('')
  const [campaignEnd,setCampaignEnd]=useState('')
  const [ocrCorrection,setOcrCorrection]=useState<Record<string,string>>({})
  const [deletionConfirmation,setDeletionConfirmation]=useState('')
  const [deletionReason,setDeletionReason]=useState('')
  const [deletionExecuteConfirmation,setDeletionExecuteConfirmation]=useState('')
  const [privacyPurpose,setPrivacyPurpose]=useState('shop_location')
  const [privacyGranted,setPrivacyGranted]=useState(false)
  const [privacyPolicyVersion,setPrivacyPolicyVersion]=useState('1.0')

  const isAdmin = role === 'Administrator'
  const endpoints = useMemo(() => {
    if (!config) return []
    if (title === 'My Dashboard' && role !== 'Mechanic') return [{label:'My account',path:'/me'}]
    if (isAdmin && title === 'Mechanic Passport') return config.endpoints.filter(e => e.admin)
    if (isAdmin && title === 'Smart Tool Bank') return config.endpoints.filter(e => e.label === 'Tool catalogue' || e.admin)
    if (isAdmin && title === 'Advocacy intelligence') return config.endpoints.filter(e => e.label !== 'My advocacy events')
    if (isAdmin && title === 'Training academy') return config.endpoints.filter(e => e.label === 'All courses (admin)')
    if (title === 'Privacy & data') return config.endpoints.filter(e => isAdmin ? e.admin : !e.admin)
    if (isAdmin && title === 'Rewards & recognition') return config.endpoints.filter(e => e.admin)
    return config.endpoints.filter(e => !e.admin || isAdmin)
  }, [config, isAdmin, role, title])

  async function load() {
    if (!config) return
    setBusy(true); setError('')
    const next: Record<string, any> = {}
    const results = await Promise.all(endpoints.map(async e => {
      try { return [e.label, await apiRequest<any>(e.path)] as const }
      catch (err) { return [e.label, { error: err instanceof Error ? err.message : 'Request failed' }] as const }
    }))
    for (const [label, payload] of results) next[label] = payload?.data ?? payload
    setDatasets(next); setBusy(false)
  }
  useEffect(() => { void load() }, [title, role])

  async function send(path: string, method: 'POST'|'PATCH'|'DELETE', body?: any) {
    setBusy(true); setError(''); setResult(null)
    try {
      const payload = await apiRequest<any>(path, { method, ...(body === undefined ? {} : {body: JSON.stringify(body)}) })
      setResult(payload?.data ?? payload)
      notify(`${method} request completed successfully.`)
      await load()
      return payload?.data ?? payload
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Request failed'
      setError(message); notify(message); return null
    } finally { setBusy(false) }
  }

  async function handleSelect(row:Json,section:string) {
    const next={...row,__source:section}
    setSelected(next)
    if(title==='Training academy' && row.course_id) {
      try {
        const payload=await apiRequest<any>(`/academy/courses/${row.course_id}`)
        setSelected({...next,...(payload.data||payload)})
      } catch(e){setError(e instanceof Error?e.message:'Could not load course details.')}
    }
    if(title==='TrustVision review' && row.evidence_id && isAdmin) {
      try {
        const payload=await apiRequest<any>(`/admin/trustvision/evidence/${row.evidence_id}`)
        const detail=payload.data||payload
        setSelected({...next,...detail})
        if(detail.ocr) {
          const fields=['invoice_number','dealer_name','invoice_date','product_name','sku','quantity','total_amount']
          setOcrCorrection(Object.fromEntries(fields.map(k=>[k,detail.ocr[k]??''])))
        }
      } catch(e){setError(e instanceof Error?e.message:'Could not load evidence details.')}
    }
  }
  async function submitOcrCorrection() {
    if(!selected?.evidence_id)return
    const body:any={}
    for(const [key,value] of Object.entries(ocrCorrection)) if(value!=='') body[key]=key==='quantity'?Number(value):value
    await send(`/admin/trustvision/evidence/${selected.evidence_id}/ocr-correction`,'PATCH',body)
  }
  async function approveKnowledge(documentId:string,approved:boolean) {
    setBusy(true);setError('')
    try {
      const form=new FormData();form.append('approved',String(approved))
      const payload=await apiRequest<any>(`/admin/copilot/documents/${documentId}/approval`,{method:'PATCH',body:form})
      setResult(payload.data);notify('Knowledge document review saved.');await load()
    } catch(e){setError(e instanceof Error?e.message:'Document review failed.')}
    finally{setBusy(false)}
  }
  async function askCopilot() {
    const payload = await send('/copilot/ask','POST',{question})
    if (payload) setResult(payload)
  }
  async function runAgent() {
    const payload = await send('/agents/run','POST',{message:question})
    if (payload) setResult(payload)
  }
  async function findNearby() {
    if(!lat||!lon){setError('Enter latitude and longitude first.');return}
    setBusy(true);setError('')
    try {
      const params=new URLSearchParams({latitude:lat,longitude:lon,radius_km:nearbyRadius})
      const payload=await apiRequest<any>(`/geo/nearby?${params}`)
      setNearbyResults(payload.data||[])
    } catch(e){setError(e instanceof Error?e.message:'Nearby search failed.')}
    finally{setBusy(false)}
  }
  async function uploadKnowledge() {
    if(!knowledgeFile||!knowledgeTitle.trim())return
    setBusy(true);setError('');setResult(null)
    try {
      const form=new FormData()
      form.append('title',knowledgeTitle);form.append('category',knowledgeCategory);form.append('language','en');form.append('file',knowledgeFile)
      const payload=await apiRequest<any>('/admin/copilot/documents',{method:'POST',body:form})
      setResult(payload.data);setKnowledgeFile(null);setKnowledgeTitle('')
      notify('Knowledge document uploaded and queued for review.')
      await load()
    } catch(e){setError(e instanceof Error?e.message:'Document upload failed.')}
    finally{setBusy(false)}
  }
  async function uploadEvidence() {
    if (!file) return
    setBusy(true); setError(''); setResult(null)
    try {
      const form = new FormData()
      form.append('evidence_kind',evidenceKind)
      form.append('file',file)
      const payload = await apiRequest<any>('/trustvision/evidence',{method:'POST',body:form})
      setResult(payload.data); setFile(null); notify('Evidence uploaded for review.')
      await load()
    } catch(e) { setError(e instanceof Error ? e.message : 'Upload failed.') }
    finally { setBusy(false) }
  }

  if (!config) return <section className="panel placeholder-panel"><h2>{title}</h2><p>This section does not yet have a dedicated interactive workspace.</p></section>

  return <div className="workspace-modules">
    <section className="panel module-intro">
      <div className="module-intro-icon"><ShieldCheck size={22}/></div>
      <div><span className="eyebrow">CONNECTED WORKSPACE</span><h2>{title}</h2><p>{config.description}</p><small>All displayed records are fetched from the authenticated backend. Empty states are not replaced with sample data.</small></div>
      <button className="button secondary compact" disabled={busy} onClick={() => void load()}><RefreshCw size={14}/> Refresh</button>
    </section>
    {error && <div className="analytics-error">{error}</div>}

    {title === 'Mechanic Passport' && !isAdmin && <section className="panel module-form">
      <h2>Add a professional skill</h2><div className="module-inline-form"><label>Skill<input value={skill} onChange={e=>setSkill(e.target.value)} placeholder="e.g. tubeless tyre repair"/></label><label>Years of experience<input type="number" min="0" max="60" value={years} onChange={e=>setYears(e.target.value)}/></label><button className="button primary compact" disabled={busy || skill.trim().length<2} onClick={async()=>{await send('/passport/me/skills','POST',{skill_name:skill,years_experience:Number(years)});setSkill('')}}><Plus size={14}/> Submit skill</button></div>
      <button className="button secondary compact" onClick={()=>void send('/passport/me/visibility','PATCH',{enabled:!Boolean(datasets['My Passport']?.public_profile_enabled),consent_version:'1.0'})}>Toggle public profile visibility</button>
      <p className="module-note">Public profile visibility requires your explicit consent. Skills remain pending until verified.</p>
    </section>}

    {(title === 'Smart Tool Bank' || title === 'Rewards & recognition') && !isAdmin && <>
      {title === 'Smart Tool Bank' && <section className="panel module-form"><h2>Request selected equipment</h2><p className="module-note">Choose a catalogue item below, then enter a reason. Stock is not reserved until approval.</p><div className="module-inline-form"><label>Reason<input value={reason} onChange={e=>setReason(e.target.value)} placeholder="Why is this tool needed?"/></label><button className="button primary compact" disabled={!selected?.product_id || reason.trim().length<5 || busy} onClick={()=>void send('/toolbank/requests','POST',{product_id:selected!.product_id,quantity:1,reason})}>Submit request</button></div></section>}
      {title === 'Rewards & recognition' && <section className="panel module-form"><h2>Request a reward redemption</h2><div className="module-inline-form"><label>Reward<input value={rewardName} onChange={e=>setRewardName(e.target.value)} placeholder="Reward name"/></label><label>Points<input type="number" min="1" value={points} onChange={e=>setPoints(e.target.value)}/></label><button className="button primary compact" disabled={!rewardName.trim()||Number(points)<1||busy} onClick={()=>void send('/rewards/redemptions','POST',{reward_name:rewardName,points_cost:Number(points)})}>Request redemption</button></div></section>}
    </>}

    {isAdmin && title === 'Smart Tool Bank' && <section className="panel module-form"><h2>Create Tool Bank catalogue item</h2><div className="module-inline-form"><label>SKU<input value={newSku} onChange={e=>setNewSku(e.target.value)}/></label><label>Tool name<input value={newProductName} onChange={e=>setNewProductName(e.target.value)}/></label><label>Category<input value={newProductType} onChange={e=>setNewProductType(e.target.value)}/></label><label>Initial stock<input type="number" min="0" value={initialQuantity} onChange={e=>setInitialQuantity(e.target.value)}/></label><button className="button primary compact" disabled={busy||newSku.trim().length<2||newProductName.trim().length<2||Number(initialQuantity)<0} onClick={async()=>{await send('/admin/toolbank/products','POST',{sku:newSku,name:newProductName,category:newProductType,initial_quantity:Number(initialQuantity),points_cost:0});setNewSku('');setNewProductName('');setNewProductType('');setInitialQuantity('0')}}>Create item</button></div></section>}
    {isAdmin && title === 'Advocacy intelligence' && <section className="panel module-form"><h2>Create advocacy campaign</h2><div className="module-inline-form"><label>Campaign code<input value={campaignCode} onChange={e=>setCampaignCode(e.target.value)}/></label><label>Title<input value={campaignTitle} onChange={e=>setCampaignTitle(e.target.value)}/></label><label>Starts at<input type="datetime-local" value={campaignStart} onChange={e=>setCampaignStart(e.target.value)}/></label><label>Ends at<input type="datetime-local" value={campaignEnd} onChange={e=>setCampaignEnd(e.target.value)}/></label><button className="button primary compact" disabled={busy||!campaignCode||!campaignTitle||!campaignStart||!campaignEnd} onClick={()=>void send('/admin/advocacy/campaigns','POST',{campaign_code:campaignCode,title:campaignTitle,starts_at:new Date(campaignStart).toISOString(),ends_at:new Date(campaignEnd).toISOString(),active:true})}>Create campaign</button></div></section>}
    {isAdmin && title === 'Product catalogue' && <section className="panel module-form"><h2>Create product catalogue entry</h2><p className="module-note">Only enter specifications from an authorised product source.</p><div className="module-inline-form"><label>SKU<input value={newSku} onChange={e=>setNewSku(e.target.value)} /></label><label>Product name<input value={newProductName} onChange={e=>setNewProductName(e.target.value)} /></label><label>Tyre type<input value={newProductType} onChange={e=>setNewProductType(e.target.value)} /></label><button className="button primary compact" disabled={busy||newSku.trim().length<2||newProductName.trim().length<2} onClick={async()=>{await send('/admin/advocacy/products','POST',{sku:newSku,product_name:newProductName,tyre_type:newProductType});setNewSku('');setNewProductName('');setNewProductType('')}}><Plus size={14}/> Add product</button></div></section>}
    {title === 'Advocacy intelligence' && <section className="panel module-form">
      <h2>Submit a product recommendation</h2><p className="module-note">Select a product in the catalogue below. A recommendation is not a verified fitment or a sale.</p><div className="module-inline-form"><label>Notes<input value={recommendNotes} onChange={e=>setRecommendNotes(e.target.value)} placeholder="Context for the recommendation"/></label><button className="button primary compact" disabled={!selected?.product_id||busy} onClick={()=>void send('/advocacy/recommendations','POST',{product_id:selected!.product_id,notes:recommendNotes})}>Submit recommendation</button></div>
      <h2 className="module-subhead">Record a fitment</h2><div className="module-inline-form"><label>Vehicle reference<input value={vehicle} onChange={e=>setVehicle(e.target.value)} placeholder="Vehicle make/model or reference"/></label><button className="button secondary compact" disabled={!selected?.product_id||!vehicle.trim()||busy} onClick={()=>void send('/advocacy/fitments','POST',{product_id:selected!.product_id,vehicle_reference:vehicle})}>Submit fitment</button></div>
      <p className="module-note">The selected catalogue item is: {selected?.product_name || 'none selected'}</p>
    </section>}

    {title === 'Advocacy intelligence' && selected?.campaign_id && !isAdmin && <section className="panel module-form"><h2>Campaign participation</h2><p className="module-note">Join the selected active campaign.</p><button className="button primary compact" disabled={busy} onClick={()=>void send(`/advocacy/campaigns/${selected.campaign_id}/participation`,'POST',{})}>Join campaign</button></section>}
    {title === 'Training academy' && <>
      {isAdmin && <section className="panel module-form"><h2>Create a draft course</h2><p className="module-note">This compact authoring flow creates one lesson and one quiz question. Review the course before publishing.</p><div className="module-inline-form"><label>Course code<input value={courseCode} onChange={e=>setCourseCode(e.target.value)}/></label><label>Course title<input value={courseTitle} onChange={e=>setCourseTitle(e.target.value)}/></label><label>Lesson title<input value={lessonTitle} onChange={e=>setLessonTitle(e.target.value)}/></label><label>Lesson content<input value={lessonContent} onChange={e=>setLessonContent(e.target.value)}/></label><label>Quiz question<input value={quizPrompt} onChange={e=>setQuizPrompt(e.target.value)}/></label><label>Options (comma separated)<input value={quizOptions} onChange={e=>setQuizOptions(e.target.value)}/></label><label>Correct option index (0-based)<input type="number" min="0" value={correctOption} onChange={e=>setCorrectOption(e.target.value)}/></label><button className="button primary compact" disabled={busy||!courseCode||!courseTitle||!lessonTitle||!quizPrompt||quizOptions.split(',').filter(x=>x.trim()).length<2} onClick={()=>void send('/admin/academy/courses','POST',{course_code:courseCode,title:courseTitle,lessons:[{title:lessonTitle,content:lessonContent,sequence:1}],questions:[{prompt:quizPrompt,options:quizOptions.split(',').map(x=>x.trim()).filter(Boolean),correct_option:Number(correctOption),sequence:1}]})}>Create draft course</button></div></section>}
      <section className="panel module-form"><h2>Course learning</h2><p className="module-note">Select a course to inspect its lessons and quiz. Enrolment is required before lesson completion and quiz submission.</p>{selected?.course_id && <><div className="module-selected-inline"><b>{selected.title}</b> · {selected.difficulty} · {selected.estimated_minutes} minutes</div>{!selected.enrollment_id && <button className="button primary compact" disabled={busy} onClick={async()=>{const enrolled=await send(`/academy/courses/${selected.course_id}/enroll`,'POST',{});if(enrolled?.enrollment_id)setSelected({...selected,enrollment_id:enrolled.enrollment_id})}}>Enrol in course</button>}{selected.enrollment_id && <div className="module-learning-list">{(selected.lessons||[]).map((lesson:any)=><div className="module-learning-item" key={lesson.lesson_id}><div><b>{lesson.sequence}. {lesson.title}</b><p>{lesson.content}</p></div><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/academy/enrollments/${selected.enrollment_id}/lessons/${lesson.lesson_id}/complete`,'POST',{})}>Mark complete</button></div>)}</div>}{selected.enrollment_id && (selected.quiz_questions||[]).map((q:any)=><label className="module-quiz-question" key={q.question_id}>{q.prompt}<select value={quizAnswers[q.question_id]??''} onChange={e=>setQuizAnswers(prev=>{const next={...prev};if(e.target.value==='')delete next[q.question_id];else next[q.question_id]=Number(e.target.value);return next})}><option value="">Choose an answer</option>{q.options.map((option:string,i:number)=><option value={i} key={i}>{option}</option>)}</select></label>)}{selected.enrollment_id && selected.quiz_questions?.length>0 && <button className="button primary compact" disabled={busy||selected.quiz_questions.some((q:any)=>quizAnswers[q.question_id]===undefined)} onClick={()=>void send(`/academy/enrollments/${selected.enrollment_id}/quiz/submit`,'POST',{answers:quizAnswers})}>Submit quiz</button>}</>}</section>
    </>}

    {title === 'Territory intelligence' && <section className="panel module-form"><h2>Save a location</h2><p className="module-note">Location sharing is optional. Discovery is enabled only when explicit consent is checked.</p><div className="module-inline-form"><label>Location name<input value={locationName} onChange={e=>setLocationName(e.target.value)} placeholder="Workshop / dealer name"/></label><label>City<input value={city} onChange={e=>setCity(e.target.value)}/></label><label>State<input value={state} onChange={e=>setState(e.target.value)}/></label><label>Latitude<input value={lat} onChange={e=>setLat(e.target.value)} placeholder="22.5726"/></label><label>Longitude<input value={lon} onChange={e=>setLon(e.target.value)} placeholder="88.3639"/></label><label className="module-consent"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/> I consent to storing this location and making it discoverable</label><button className="button primary compact" disabled={busy||!locationName.trim()||!city.trim()||!state.trim()||!lat||!lon} onClick={()=>void send('/geo/locations','POST',{location_type:'mechanic_shop',display_name:locationName,city,state,latitude:Number(lat),longitude:Number(lon),location_consent:consent,discoverable:consent,country:'India'})}>Save location</button></div><div className="module-inline-form"><label>Discovery radius (km)<input type="number" min="0.1" max="100" value={nearbyRadius} onChange={e=>setNearbyRadius(e.target.value)}/></label><button className="button secondary compact" disabled={busy||!lat||!lon} onClick={()=>void findNearby()}><MapPin size={14}/> Find opted-in nearby locations</button></div>{nearbyResults.length>0&&<Records title="Nearby opted-in locations" value={nearbyResults}/>}</section>}

    {title === 'TrustVision review' && <section className="panel module-form"><h2>Submit image evidence</h2><p className="module-note">JPEG, PNG or WebP only. Maximum size and image checks are enforced by the backend.</p><div className="module-inline-form"><label>Evidence type<select value={evidenceKind} onChange={e=>setEvidenceKind(e.target.value)}><option value="invoice">Invoice</option><option value="fitment">Fitment image</option><option value="product_image">Product image</option><option value="product_qr">Product QR</option></select></label><label>Image file<input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>setFile(e.target.files?.[0]||null)}/></label><button className="button primary compact" disabled={!file||busy} onClick={()=>void uploadEvidence()}>Upload evidence</button></div></section>}

    {isAdmin && title === 'AI Copilot' && <section className="panel module-form"><h2>Upload knowledge document</h2><p className="module-note">Supported formats and extraction limits are enforced by the backend. New documents remain excluded from answers until approved.</p><div className="module-inline-form"><label>Document title<input value={knowledgeTitle} onChange={e=>setKnowledgeTitle(e.target.value)} /></label><label>Category<select value={knowledgeCategory} onChange={e=>setKnowledgeCategory(e.target.value)}>{['general','product','fitment','warranty','training','safety','policy'].map(x=><option key={x}>{x}</option>)}</select></label><label>File<input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg" onChange={e=>setKnowledgeFile(e.target.files?.[0]||null)}/></label><button className="button primary compact" disabled={busy||!knowledgeFile||!knowledgeTitle.trim()} onClick={()=>void uploadKnowledge()}>Upload for review</button></div></section>}
    {title === 'AI Copilot' && <section className="panel module-form"><h2>Ask the approved knowledge base</h2><textarea className="module-question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about documented product, fitment, warranty or safety information…"/><div className="module-inline-form"><button className="button primary compact" disabled={busy||question.trim().length<3} onClick={()=>void askCopilot()}><BookOpen size={14}/> Ask Copilot</button><button className="button secondary compact" disabled={busy||question.trim().length<3} onClick={()=>void runAgent()}><Bot size={14}/> Run read-only agents</button></div><p className="module-note">Copilot answers only from approved knowledge documents. Agent workflows are read-only; they do not execute business actions.</p></section>}


    {title === 'Privacy & data' && !isAdmin && <section className="panel module-form">
      <h2>Request account deletion</h2>
      <p className="module-note">This submits a request for administrator review. Your account stays active until the request is approved and a separate administrator explicitly executes the process. Direct profile identifiers and user-submitted TrustVision evidence are removed; some historical business, reward, learning and audit records may be retained in pseudonymized form where approved policy requires it.</p>
      <h2>Consent preferences</h2>
      <p className="module-note">Withdraw optional purposes when you no longer want the associated processing. Withdrawal disables location discovery where applicable.</p>
      <div className="module-inline-form">
        <label>Consent purpose<select value={privacyPurpose} onChange={e=>setPrivacyPurpose(e.target.value)}><option value="shop_location">Shop location</option><option value="geolocation_discovery">Geolocation discovery</option><option value="product_advocacy">Product advocacy</option><option value="training_analytics">Training analytics</option></select></label>
        <label>Policy version<input value={privacyPolicyVersion} maxLength={30} onChange={e=>setPrivacyPolicyVersion(e.target.value)}/></label>
        <label className="module-consent"><input type="checkbox" checked={privacyGranted} onChange={e=>setPrivacyGranted(e.target.checked)}/> Grant this optional consent (unchecked withdraws)</label>
        <button className="button secondary compact" disabled={busy||!privacyPolicyVersion.trim()} onClick={()=>void send(`/me/privacy/consents/${privacyPurpose}`,'POST',{granted:privacyGranted,policy_version:privacyPolicyVersion})}>Save consent preference</button>
      </div>
      <div className="module-inline-form">
        <label>Reason (optional)<input value={deletionReason} maxLength={500} onChange={e=>setDeletionReason(e.target.value)} placeholder="Optional reason"/></label>
        <label>Type DELETE MY ACCOUNT to confirm<input value={deletionConfirmation} onChange={e=>setDeletionConfirmation(e.target.value)} placeholder="DELETE MY ACCOUNT"/></label>
        <button className="button danger compact" disabled={busy||deletionConfirmation!=='DELETE MY ACCOUNT'} onClick={async()=>{const done=await send('/me/privacy/deletion-requests','POST',{confirmation:deletionConfirmation,reason:deletionReason});if(done){setDeletionConfirmation('');setDeletionReason('')}}}>Submit deletion request</button>
      </div>
    </section>}
    {title === 'Privacy & data' && isAdmin && selected?.__source === 'Deletion requests (admin)' && <section className="panel module-form">
      <h2>Review account deletion request</h2>
      <p className="module-note">Request {selected.request_id} · Account reference {selected.user_id} · Status {selected.status}. Approve only after checking the request and applicable retention/legal holds. Execution is irreversible for the direct profile data and uploaded evidence covered by this workflow.</p>
      {selected.status === 'pending' && <div className="module-inline-form">
        <button className="button primary compact" disabled={busy} onClick={async()=>{const done=await send(`/admin/privacy/deletion-requests/${selected.request_id}/decision`,'PATCH',{approved:true,note:'Reviewed and approved under the approved privacy process'});if(done)setSelected({...selected,status:'approved'})}}>Approve request</button>
        <button className="button secondary compact" disabled={busy} onClick={async()=>{const done=await send(`/admin/privacy/deletion-requests/${selected.request_id}/decision`,'PATCH',{approved:false,note:'Request not approved; user may contact support'});if(done)setSelected({...selected,status:'rejected'})}}>Reject request</button>
      </div>}
      {selected.status === 'approved' && <div className="module-inline-form">
        <label>Type EXECUTE ACCOUNT ERASURE to confirm<input value={deletionExecuteConfirmation} onChange={e=>setDeletionExecuteConfirmation(e.target.value)} placeholder="EXECUTE ACCOUNT ERASURE"/></label>
        <button className="button danger compact" disabled={busy||deletionExecuteConfirmation!=='EXECUTE ACCOUNT ERASURE'} onClick={async()=>{const done=await send(`/admin/privacy/deletion-requests/${selected.request_id}/execute`,'POST',{confirmation:deletionExecuteConfirmation});if(done){setDeletionExecuteConfirmation('');setSelected(null)}}}>Execute approved erasure</button>
      </div>}
    </section>}

    {isAdmin && selected?.__source === 'Pending skills (admin)' && selected?.skill_id && <section className="panel module-form"><h2>Verify submitted skill</h2><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/passport/skills/${selected.skill_id}/verification`,'PATCH',{approved:true})}>Verify skill</button><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/admin/passport/skills/${selected.skill_id}/verification`,'PATCH',{approved:false})}>Reject skill</button></div></section>}
    {isAdmin && selected?.__source === 'Pending requests (admin)' && <section className="panel module-form"><h2>Review selected Tool Bank request</h2><p className="module-note">{selected.tool} · {selected.quantity} · {selected.mechanic_code}</p><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/toolbank/requests/${selected.request_id}`,'PATCH',{approved:true,note:'Approved by authorised administrator'})}>Approve request</button><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/admin/toolbank/requests/${selected.request_id}`,'PATCH',{approved:false,note:'Rejected by authorised administrator'})}>Reject request</button></div></section>}
    {isAdmin && selected?.evidence_id && selected?.ocr && <section className="panel module-form"><h2>Evidence details and OCR correction</h2><p className="module-note">Corrections are recorded as manual review metadata. Preserve the original extracted values in your review notes.</p><div className="module-inline-form">{Object.entries(ocrCorrection).map(([key,value])=><label key={key}>{key.replace(/_/g,' ')}<input value={value} onChange={e=>setOcrCorrection(prev=>({...prev,[key]:e.target.value}))}/></label>)}</div><button className="button primary compact" disabled={busy} onClick={()=>void submitOcrCorrection()}>Save OCR corrections</button></section>}
    {isAdmin && selected?.__source === 'Pending redemptions (admin)' && selected?.redemption_id && <section className="panel module-form"><h2>Review reward redemption</h2><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/rewards/redemptions/${selected.redemption_id}`,'PATCH',{approved:true,note:'Approved by authorised administrator'})}>Approve redemption</button><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/admin/rewards/redemptions/${selected.redemption_id}`,'PATCH',{approved:false,note:'Rejected by authorised administrator'})}>Reject redemption</button></div></section>}
    {isAdmin && selected?.__source === 'Pending requests (admin)' && selected?.request_id && selected?.status === 'approved' && <section className="panel module-form"><h2>Fulfil approved tool request</h2><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/toolbank/requests/${selected.request_id}/fulfil`,'PATCH',{})}>Mark as fulfilled</button></section>}
    {isAdmin && selected?.__source === 'Review queue' && selected?.case_id && <section className="panel module-form"><h2>TrustVision human review</h2><p className="module-note">Case {selected.case_id} · Risk {selected.risk_level} · Score {selected.risk_score}. Automated risk indicators are not a fraud finding.</p><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/trustvision/cases/${selected.case_id}/decision`,'PATCH',{decision:'cleared',reviewer_note:'Reviewed and cleared by authorised reviewer'})}>Clear case</button><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/admin/trustvision/cases/${selected.case_id}/decision`,'PATCH',{decision:'needs_information',reviewer_note:'Additional information requested'})}>Needs information</button><button className="button danger compact" disabled={busy} onClick={()=>void send(`/admin/trustvision/cases/${selected.case_id}/decision`,'PATCH',{decision:'confirmed_fraud',reviewer_note:'Confirmed after human evidence review'})}>Confirm fraud</button></div></section>}
    {isAdmin && selected?.__source === 'recommendations' && selected?.id && <section className="panel module-form"><h2>Verify recommendation</h2><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/advocacy/recommendations/${selected.id}/verification`,'PATCH',{approved:true,note:'Verified by authorised administrator'})}>Verify</button><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/admin/advocacy/recommendations/${selected.id}/verification`,'PATCH',{approved:false,note:'Rejected by authorised administrator'})}>Reject</button></div></section>}
    {isAdmin && selected?.__source === 'fitments' && selected?.id && <section className="panel module-form"><h2>Verify fitment</h2><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/advocacy/fitments/${selected.id}/verification`,'PATCH',{approved:true,note:'Verified by authorised administrator'})}>Verify</button><button className="button secondary compact" disabled={busy} onClick={()=>void send(`/admin/advocacy/fitments/${selected.id}/verification`,'PATCH',{approved:false,note:'Rejected by authorised administrator'})}>Reject</button></div></section>}
    {isAdmin && selected?.__source === 'Knowledge documents (admin)' && selected?.document_id && selected?.status === 'pending_review' && <section className="panel module-form"><h2>Approve knowledge document</h2><p className="module-note">Approve only after checking the source and document content.</p><div className="module-inline-form"><button className="button primary compact" disabled={busy} onClick={()=>void approveKnowledge(selected.document_id,true)}>Approve document</button><button className="button secondary compact" disabled={busy} onClick={()=>void approveKnowledge(selected.document_id,false)}>Reject document</button></div></section>}
    {isAdmin && selected?.__source === 'All courses (admin)' && selected?.course_id && <section className="panel module-form"><h2>Publish selected course</h2><button className="button primary compact" disabled={busy} onClick={()=>void send(`/admin/academy/courses/${selected.course_id}/publish`,'PATCH')}>Publish course</button></section>}
    {endpoints.map(endpoint => <Records key={endpoint.path} title={endpoint.label} value={datasets[endpoint.label]} onAction={(row,section)=>void handleSelect(row,section)}/>)}
    {result && <section className="panel module-result"><div className="panel-head"><div><h2>Latest operation result</h2><p>Response returned by the backend</p></div><CheckCircle2 size={18}/></div><pre>{JSON.stringify(result,null,2)}</pre></section>}
    {selected && <div className="module-selected">Selected record: {pretty(selected.product_name||selected.name||selected.title||selected.course?.title||selected.product_id||selected.course_id||selected.id)} <button onClick={()=>setSelected(null)}>Clear</button></div>}
  </div>
}
