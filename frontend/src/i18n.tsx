import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export type Lang = 'en' | 'hi';

const en = {
  'dashboard.title': 'Infrastructure Risk Overview',
  'dashboard.subtitle': "Predictive intelligence for India's infrastructure project portfolio",
  'kpi.totalProjects': 'Total Projects',
  'kpi.totalProjectsSub': 'Currently monitored',
  'kpi.highRisk': 'High Risk Projects',
  'kpi.highRiskSub': 'Require attention',
  'kpi.scheduleRisk': 'Schedule Risk',
  'kpi.scheduleRiskSub': 'Projects showing delay signals',
  'kpi.costRisk': 'Cost Risk',
  'kpi.costRiskSub': 'Projects showing escalation signals',
  'kpi.portfolioValue': 'Portfolio Value',
  'kpi.portfolioValueSub': 'Original approved cost',
  'kpi.revisedValue': 'Revised Value',
  'kpi.revisedValueSub': 'Current revised cost',
  'dashboard.attentionTitle': 'Projects Requiring Immediate Attention',
  'dashboard.attentionSub':
    'Projects with elevated probability of cost escalation, schedule delay, or implementation risk.',
  'dashboard.viewAll': 'View all projects',
  'table.project': 'Project',
  'table.ministry': 'Ministry',
  'table.sector': 'Sector',
  'table.state': 'State',
  'table.progress': 'Progress',
  'table.costOverrun': 'Cost Overrun',
  'table.delayProb': 'Delay Probability',
  'table.riskScore': 'Risk Score',
  'table.status': 'Status',
  'chart.riskDistribution': 'Portfolio Risk Distribution',
  'chart.riskDistributionSub': 'Share of monitored projects by current risk level.',
  'chart.riskTrend': 'Portfolio Risk Trend',
  'chart.riskTrendSub': 'Monthly risk classification over the last six months.',
  'dashboard.analyticsCta': 'Dive deeper into portfolio analytics',
  'dashboard.analyticsCtaSub':
    'Sector comparisons, cost overrun drivers, delay analysis, and ministry-wise risk rankings.',
  'dashboard.openAnalytics': 'Open Analytics',
  'common.retry': 'Retry',
  'login.governmentLine': 'Government of India · Infrastructure Risk Intelligence',
  'login.ministryLine': 'Ministry of Electronics & Information Technology · Digital Services',
  'login.live': 'Live',
  'login.title': 'Government Portal',
  'login.subtitle': 'Secure access to the Government Digital Services Portal',
  'login.signIn': 'Sign In',
  'login.credentialsLine': 'Enter your credentials to access your account.',
  'login.emailLabel': 'Email / Government ID',
  'login.passwordLabel': 'Password',
  'login.passwordPlaceholder': 'Enter your password',
  'login.rememberMe': 'Remember me',
  'login.forgotPassword': 'Forgot password?',
  'login.signingIn': 'Signing in…',
  'login.protected': 'Your information is protected using secure authentication.',
  'login.noAccount': "Don't have an account?",
  'login.requestAccess': 'Request access',
  'login.demoCredentials': 'Demo credentials',
  'login.helpReset': 'Please contact your departmental administrator to reset your password.',
} as const;

const hi: Record<keyof typeof en, string> = {
  'dashboard.title': 'अवसंरचना जोखिम अवलोकन',
  'dashboard.subtitle': 'भारत के अवसंरचना परियोजना पोर्टफोलियो के लिए पूर्वानुमानित बुद्धिमत्ता',
  'kpi.totalProjects': 'कुल परियोजनाएँ',
  'kpi.totalProjectsSub': 'वर्तमान में निगरानी',
  'kpi.highRisk': 'उच्च जोखिम परियोजनाएँ',
  'kpi.highRiskSub': 'ध्यान देने की आवश्यकता',
  'kpi.scheduleRisk': 'अनुसूची जोखिम',
  'kpi.scheduleRiskSub': 'विलंब संकेत दिखाने वाली परियोजनाएँ',
  'kpi.costRisk': 'लागत जोखिम',
  'kpi.costRiskSub': 'लागत वृद्धि संकेत दिखाने वाली परियोजनाएँ',
  'kpi.portfolioValue': 'पोर्टफोलियो मूल्य',
  'kpi.portfolioValueSub': 'मूल स्वीकृत लागत',
  'kpi.revisedValue': 'संशोधित मूल्य',
  'kpi.revisedValueSub': 'वर्तमान संशोधित लागत',
  'dashboard.attentionTitle': 'तत्काल ध्यान देने की आवश्यकता वाली परियोजनाएँ',
  'dashboard.attentionSub':
    'लागत वृद्धि, अनुसूची विलंब, या कार्यान्वयन जोखिम की उच्च संभावना वाली परियोजनाएँ।',
  'dashboard.viewAll': 'सभी परियोजनाएँ देखें',
  'table.project': 'परियोजना',
  'table.ministry': 'मंत्रालय',
  'table.sector': 'क्षेत्र',
  'table.state': 'राज्य',
  'table.progress': 'प्रगति',
  'table.costOverrun': 'लागत वृद्धि',
  'table.delayProb': 'विलंब संभावना',
  'table.riskScore': 'जोखिम स्कोर',
  'table.status': 'स्थिति',
  'chart.riskDistribution': 'पोर्टफोलियो जोखिम वितरण',
  'chart.riskDistributionSub': 'वर्तमान जोखिम स्तर के अनुसार निगरानी की गई परियोजनाओं का हिस्सा।',
  'chart.riskTrend': 'पोर्टफोलियो जोखिम प्रवृत्ति',
  'chart.riskTrendSub': 'पिछले छह महीनों में मासिक जोखिम वर्गीकरण।',
  'dashboard.analyticsCta': 'पोर्टफोलियो एनालिटिक्स में और गहराई से जाएँ',
  'dashboard.analyticsCtaSub':
    'क्षेत्र तुलना, लागत वृद्धि के कारक, विलंब विश्लेषण, और मंत्रालय-वार जोखिम रैंकिंग।',
  'dashboard.openAnalytics': 'एनालिटिक्स खोलें',
  'common.retry': 'पुनः प्रयास करें',
  'login.governmentLine': 'भारत सरकार · अवसंरचना जोखिम बुद्धिमत्ता',
  'login.ministryLine': 'इलेक्ट्रॉनिक्स एवं सूचना प्रौद्योगिकी मंत्रालय · डिजिटल सेवाएँ',
  'login.live': 'लाइव',
  'login.title': 'सरकारी पोर्टल',
  'login.subtitle': 'सरकारी डिजिटल सेवा पोर्टल तक सुरक्षित पहुँच',
  'login.signIn': 'साइन इन',
  'login.credentialsLine': 'अपने खाते तक पहुँचने के लिए अपनी साख दर्ज करें।',
  'login.emailLabel': 'ईमेल / सरकारी आईडी',
  'login.passwordLabel': 'पासवर्ड',
  'login.passwordPlaceholder': 'अपना पासवर्ड दर्ज करें',
  'login.rememberMe': 'मुझे याद रखें',
  'login.forgotPassword': 'पासवर्ड भूल गए?',
  'login.signingIn': 'साइन इन हो रहा है…',
  'login.protected': 'आपकी जानकारी सुरक्षित प्रमाणीकरण द्वारा सुरक्षित है।',
  'login.noAccount': 'खाता नहीं है?',
  'login.requestAccess': 'पहुँच का अनुरोध करें',
  'login.demoCredentials': 'डेमो साख',
  'login.helpReset': 'पासवर्ड रीसेट करने के लिए अपने विभागीय प्रशासक से संपर्क करें।',
};

export type TranslationKey = keyof typeof en;

const dictionaries: Record<Lang, Record<TranslationKey, string>> = { en, hi };

const LANG_KEY = 'govrisk-lang';

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: TranslationKey) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    if (typeof window === 'undefined') return 'en';
    return window.localStorage.getItem(LANG_KEY) === 'hi' ? 'hi' : 'en';
  });

  useEffect(() => {
    window.localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const t = (key: TranslationKey) =>
    dictionaries[lang][key] ?? dictionaries.en[key];

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within an I18nProvider');
  return ctx;
}