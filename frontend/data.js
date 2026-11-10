/* Sample data for the prototype. Legal classifications here are SAMPLE VALUES for layout only;
   the real values come from the advisor-reviewed dataset (PLAN_AI.md, D-01). */
const SECTIONS = []; // filled from /api/v1/sections at runtime
const LAWYERS = [
  { id: 'l1', type: 'lawyer', name: 'Adv. Sample One', ini: 'S1', city: 'Islamabad', spec: ['Criminal law', 'Bail'], pro: true, phone: '0300 5550101', bio: 'Criminal defence lawyer with ten years of practice in the Islamabad High Court. Offers free bail advice on weekends.' },
  { id: 'l2', type: 'lawyer', name: 'Adv. Sample Two', ini: 'S2', city: 'Rawalpindi', spec: ['Criminal law', 'Habeas corpus'], pro: true, phone: '0321 5550102', bio: 'Handles illegal detention and habeas corpus petitions before the Lahore High Court Rawalpindi Bench.' },
  { id: 'l3', type: 'lawyer', name: 'Adv. Sample Three', ini: 'S3', city: 'Lahore', spec: ['Family law', 'Harassment'], pro: false, phone: '0333 5550103', bio: 'Advises on harassment complaints and protective orders.' },
  { id: 'l4', type: 'lawyer', name: 'Adv. Sample Four', ini: 'S4', city: 'Karachi', spec: ['Criminal law'], pro: true, phone: '0345 5550104', bio: 'Practises in Sindh High Court, criminal and bail matters.' },
  { id: 'l5', type: 'lawyer', name: 'Adv. Sample Five', ini: 'S5', city: 'Peshawar', spec: ['Bail', 'Harassment'], pro: false, phone: '0311 5550105', bio: 'Bail and complaint drafting, Peshawar High Court.' },
  { id: 'o1', type: 'org', name: 'Sample Organisation One', ini: 'O1', city: 'Islamabad', spec: ['Legal aid', 'Detention monitoring'], pro: true, phone: '051 5550201', bio: 'Sample organisation entry: legal aid clinic and detention monitoring.' },
  { id: 'o2', type: 'org', name: 'Sample Organisation Two', ini: 'O2', city: 'Lahore', spec: ['Legal aid'], pro: true, phone: '042 5550202', bio: 'Sample organisation entry: walk-in legal information desk.' },
];
const GUIDES = [
  { id: 'lawful-arrest-steps', cat: 'Lawful arrest', title: 'Lawful arrest: what the police must do', sum: 'Steps a lawful arrest must follow', steps: ['The officer should tell you the reason for the arrest.', 'You should be taken to the police station or before a Magistrate without unnecessary delay.', 'You must be produced before a Magistrate within twenty-four hours, excluding travel time (Constitution Article 10, CrPC section 61).', 'You have the right to consult a lawyer of your choice.', 'Ask for a written record of the arrest and the time it was made.', 'Stay calm, do not resist, and do not sign a blank or unread paper.'], cite: 'CrPC 54, CrPC 61' },
  { id: 'art-10-safeguards', cat: 'Your rights', title: 'Article 10: safeguards as to arrest and detention', sum: 'Constitutional safeguards when arrested', steps: ['No person may be detained without being informed, as soon as possible, of the grounds for arrest.', 'The person has the right to consult and be defended by a lawyer of their choice.', 'The person must be produced before a Magistrate within twenty-four hours of arrest.', 'Detention beyond twenty-four hours needs the authority of a Magistrate.'], cite: 'Constitution Art. 10' },
  { id: 'art-10a-fair-trial', cat: 'Your rights', title: 'Article 10A: right to a fair trial', sum: 'Fair trial and due process', steps: ['Everyone is entitled to a fair trial and due process in the determination of their rights and any criminal charge.', 'This includes a hearing by an independent court and a fair opportunity to defend yourself.', 'Keep copies of every paper you receive from the police or the court.'], cite: 'Constitution Art. 10A' },
  { id: 'bail-process-overview', cat: 'Bail roadmap', title: 'Bail: step-by-step roadmap', sum: 'Documents, court process and timelines', steps: ['Find out whether the offence is bailable or non-bailable (use Check a section).', 'For a bailable offence bail is a matter of right: ask for it at the police station or the court.', 'For a non-bailable offence a lawyer files a bail application before the court.', 'Gather your CNIC copy, the FIR copy, surety papers and two sureties.', 'The court hears the state and the defence and then decides.', 'If bail is refused you can apply to a higher court through a lawyer.'], cite: 'CrPC 496, CrPC 497' },
];
const TEMPLATES = [
  { id: 'fir-application', title: 'Application to register an FIR', sum: 'Ask the police to register your complaint', fields: [['Your full name', 'text', 'Sample Citizen'], ['Your CNIC', 'text', '35202-1234567-1'], ['Police station', 'text', 'Sample Police Station'], ['Date of incident', 'date', '2026-09-25'], ['What happened', 'ta', 'I was stopped near F-6 Markaz and my phone was taken.']] },
  { id: 'harassment-complaint', title: 'Harassment complaint', sum: 'Complaint about harassment by a person or an official', fields: [['Your full name', 'text', ''], ['Against whom', 'text', ''], ['Place of incident', 'text', ''], ['Date of incident', 'date', ''], ['Details', 'ta', '']] },
  { id: 'illegal-detention-notice', title: 'Illegal detention notice', sum: 'Formal notice about detention without lawful authority', fields: [['Detained person name', 'text', ''], ['Detained since (date)', 'date', ''], ['Place of detention', 'text', ''], ['Officer in charge', 'text', ''], ['Details', 'ta', '']] },
  { id: 'habeas-corpus-draft', title: 'Habeas corpus petition draft', sum: 'Draft petition to produce a detained person before the court', fields: [['Petitioner name', 'text', ''], ['Detained person name', 'text', ''], ['Last known place', 'text', ''], ['Date of detention', 'date', ''], ['Grounds', 'ta', '']] },
];
const ALERTS = [
  { id: 'a1', district: 'Rawalpindi', ago: '2 min ago', person: 'Sample Citizen', phone: '0300 1112233', live: true },
  { id: 'a2', district: 'Islamabad', ago: '14 min ago', person: 'Sample Citizen B', phone: '0312 4445566', live: false },
];
const DISTRICTS = ['Islamabad', 'Rawalpindi', 'Lahore', 'Karachi', 'Peshawar', 'Quetta', 'Faisalabad', 'Multan'];
const CATEGORIES = ['Illegal detention', 'Harassment', 'Misuse of section', 'Extortion', 'Physical abuse', 'Other'];
const VERIFY_QUEUE = [
  { id: 'v1', role: 'lawyer', name: 'Adv. Sample Six', extra: 'Bar Council no. ICT-2231', city: 'Islamabad', ago: '1 day ago' },
  { id: 'v2', role: 'lawyer', name: 'Adv. Sample Seven', extra: 'Bar Council no. LHR-8842', city: 'Lahore', ago: '2 days ago' },
  { id: 'v3', role: 'ngo_monitor', name: 'Sample NGO Monitor', extra: 'Sample NGO', city: 'Karachi', ago: '3 days ago' },
];
const ADMIN_INC = [
  { id: 'i1', cat: 'Illegal detention', district: 'Rawalpindi', date: '24 Sep', files: 2, status: 'pending', desc: 'Held for a night at the station without being told the reason. Released next morning without any paper.' },
  { id: 'i2', cat: 'Harassment', district: 'Lahore', date: '22 Sep', files: 0, status: 'pending', desc: 'Repeatedly stopped and asked for money at a checkpoint.' },
  { id: 'i3', cat: 'Misuse of section', district: 'Karachi', date: '20 Sep', files: 1, status: 'approved', desc: 'A non-cognizable complaint was treated as a cognizable offence.' },
];
const ANALYTICS = { 'Illegal detention': [['Rawalpindi', 14], ['Lahore', 11], ['Karachi', 9], ['Islamabad', 6], ['Peshawar', 4]], 'Harassment': [['Lahore', 12], ['Karachi', 10], ['Islamabad', 7], ['Rawalpindi', 5], ['Multan', 3]], 'All': [['Lahore', 23], ['Rawalpindi', 19], ['Karachi', 19], ['Islamabad', 13], ['Peshawar', 8], ['Multan', 5]] };
const HASH = '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08';
ST.evidence = [
  { id: 'e1', type: 'video', name: 'Video 14:32', size: '182 MB', when: '28 Sep 2026, 21:14 PKT', status: 'complete' },
  { id: 'e2', type: 'audio', name: 'Audio 03:10', size: '3.1 MB', when: '27 Sep 2026, 18:02 PKT', status: 'complete' },
  { id: 'e3', type: 'photo', name: 'Photo 1', size: '2.4 MB', when: '27 Sep 2026, 17:55 PKT', status: 'complete' },
];
ST.incidents = [
  { id: 'm1', cat: 'Illegal detention', district: 'Rawalpindi', date: '24 Sep 2026', status: 'pending', files: 2 },
  { id: 'm2', cat: 'Harassment', district: 'Islamabad', date: '12 Sep 2026', status: 'approved', files: 0 },
];
