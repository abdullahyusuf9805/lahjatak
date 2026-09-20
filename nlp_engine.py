import os
import streamlit as st
from google import genai

# جلب مفتاح API بأمان من متغيرات البيئة في Streamlit Secrets أو GitHub Secrets
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # محاولة جلبه من st.secrets كخيار احتياطي لمنصة Streamlit Cloud
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        raise ValueError("GEMINI_API_KEY is not set in the environment variables.")

# تهيئة عميل الذكاء الاصطناعي
client = genai.Client(api_key=api_key)

# تهيئة قاعدة البيانات والتحليل الصرفي مرة واحدة في الذاكرة
print("Loading Morphology DB...")
_db = MorphologyDB.builtin_db()
_analyzer = Analyzer(_db)

# تهيئة عميل الذكاء الاصطناعي
client = genai.Client(api_key=config.GEMINI_API_KEY)


def load_lexicon():
    print("Loading MADAR dataset...")
    df = pd.read_csv(
        'data/MADAR_Lexicon_Saudi.tsv', 
        sep='\t', 
        encoding='utf-8', 
        engine='python', 
        on_bad_lines='skip',
        quoting=csv.QUOTE_NONE
    )
    df = df[['MSA', 'Dialect', 'CODA', 'CAPHI']].dropna(subset=['MSA', 'Dialect', 'CODA'])
    df['CAPHI'] = df['CAPHI'].fillna('')
    return df

def clean_punctuation_spacing(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+([؟!\.,،؛:\?])', r'\1', text)

def normalize_arabic(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'[أإآ]', 'ا', text)
    return text.strip()

def format_pronunciation(caphi_text):
    if not isinstance(caphi_text, str) or not caphi_text:
        return ""
    
    # تنظيف وتنسيق نص الـ CAPHI ليصبح نظيفاً وواضحاً (مثل eesh tabgha mnny)
    cleaned = caphi_text.replace('2', '').replace('_', ' ')
    
    # إزالة التكرارات الناتجة عن الحركات أو الرموز المعجمية المتلاصقة
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # دمج الحروف المفصولة بشكل خاطئ إن وجدت لتقريب شكل النطق
    # (مثال: تحويل الرموز الطويلة أو المكررة إلى شكلها الطبيعي المقروء)
    cleaned = cleaned.replace('ee sh', 'eesh').replace('th', 'th').replace('sh', 'sh')
    
    return cleaned

def fallback_pronunciation(word):
    mapping = {
        'ا':'a', 'أ':'a', 'إ':'i', 'آ':'aa', 'ب':'b', 'ت':'t', 'ث':'th',
        'ج':'j', 'ح':'h', 'خ':'kh', 'د':'d', 'ذ':'dh', 'ر':'r', 'ز':'z',
        'س':'s', 'ش':'sh', 'ص':'s', 'ض':'d', 'ط':'t', 'ظ':'z', 'ع':'3',
        'غ':'gh', 'ف':'f', 'ق':'g', 'ك':'k', 'ل':'l', 'م':'m', 'ن':'n',
        'ه':'h', 'ة':'a', 'و':'w', 'ي':'y', 'ى':'a', 'ء':''
    }
    return "".join([mapping.get(c, c) for c in word])

# =====================================================================
# 1. دالة الترجمة من الفصحى إلى العامية (الجذور + القاموس + Gemini المصفاة + CAPHI الحقيقي)
# =====================================================================
def process_fusha(text, lexicon_df, dialect_choice="اللهجات السعودية"):
    clean_text = text.replace('؟', '').replace('!', '').replace('.', '').strip()
    words = clean_text.split()
    
    hejazi_raw_options = []
    najdi_raw_options = []
    
    normalized_msa_col = lexicon_df['MSA'].apply(normalize_arabic)

    # الخطوة الأولى: استخراج الجذور والمشتقات والبحث الشامل في القاموس
    for word in words:
        lookup_targets = {normalize_arabic(word)}
        try:
            analyses = _analyzer.analyze(word)
            for analysis in analyses:
                lemma = analysis.get('lex')
                if lemma:
                    lookup_targets.add(normalize_arabic(lemma))
        except:
            pass

        jed_words = []
        riy_words = []
        
        for target in lookup_targets:
            search_pattern = fr'(?:^|،|,)\s*{target}\s*(?:،|,|$)'
            mask_jed = (lexicon_df['Dialect'] == 'JED') & (normalized_msa_col.str.contains(search_pattern, regex=True, na=False))
            mask_riy = (lexicon_df['Dialect'] == 'RIY') & (normalized_msa_col.str.contains(search_pattern, regex=True, na=False))
            
            jed_match = lexicon_df[mask_jed]
            riy_match = lexicon_df[mask_riy]
            
            if not jed_match.empty:
                jed_words.extend(jed_match['CODA'].dropna().astype(str).unique().tolist())
            if not riy_match.empty:
                riy_words.extend(riy_match['CODA'].dropna().astype(str).unique().tolist())

        if not jed_words:
            jed_words = [word]
        if not riy_words:
            riy_words = [word]
            
        hejazi_raw_options.append(list(dict.fromkeys(jed_words)))
        najdi_raw_options.append(list(dict.fromkeys(riy_words)))

    # الخطوة الثانية: تمرير البدائل المستخرجة لـ Gemini لاختيار الأصح سياقياً بحد أقصى 3 خيارات
    try:
        selection_prompt = f"""
        أنت لغوي خبير باللهجة الحجازية والنجدية السعودية.
        العبارة الفصحى الأصلية هي: "{clean_text}"
        
        مهمتك تصفية واختيار التركيب الأنسب والأكثر طبيعية في الكلام اليومي:
        - البدائل الحجازية المتاحة: {hejazi_raw_options}
        - البدائل النجدية المتاحة: {najdi_raw_options}
        
        تعليمات صارمة جداً ضد الهلوسة واختلاق الخيارات:
        1. **ممنوع منعاً باتاً اختلاق أو تأليف خيار ثانٍ وهمي.** إذا كانت الجملة تؤدي المعنى بخيار واحد صحيح ومألوف (مثل "تقدر تجي عندي؟")، ضع **خياراً واحداً فقط** في المصفوفة (`["الخيار الصحيح"]`). الجودة والصحة اللغوية أهم بكثير من إظهار خيارين.
        2. لا تضف خياراً ثانياً إلا إذا كان هناك مرادف حقيقي ومستخدم بنسبة 100% في الشارع السعودي (مثل وجود خيارين حقيقيين ومشهورين فعلاً). وإذا لم يوجد، اكتفِ بخيار واحد فقط تماماً لتجنب الهلوسة.
        3. في قسم الشرح (timeline)، اشرح كل كلمة استبدلت وحدها في جملة مستقلة، محاطة بأقواس مزدوجة مضاعفة حصرياً ((الكلمة)) لكي تتلون تلقائياً في واجهة التطبيق.
        4. صيغة الشرح الإلزامية:
           "💡 في اللهجة الحجازية يُستخدم لفظ ((الكلمة_العامية)) مكانَ ((الكلمة_الفصحى))."
           أو للنجدية:
           "💡 في اللهجة النجدية يُستخدم لفظ ((الكلمة_العامية)) مكانَ ((الكلمة_الفصحى))."
        5. أضف علامة الترقيم المناسبة في النهاية مرة واحدة.
        
        أريد النتيجة بصيغة JSON فقط بدون أي نصوص إضافية، بالشكل التالي:
        {{
            "hejazi_sentences": ["الخيار الصحيح الوحيد"],
            "najdi_sentences": ["الخيار الصحيح الوحيد"],
            "timeline": [
                "💡 في اللهجة الحجازية يُستخدم لفظ ((الكلمة_العامية)) مكانَ ((الكلمة_الفصحى))."
            ]
        }}
        """
        
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=selection_prompt,
        )
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        result_data = json.loads(res_text)
        
        hejazi_sentences = result_data.get("hejazi_sentences", [clean_text])[:3]
        najdi_sentences = result_data.get("najdi_sentences", [clean_text])[:3]
        timeline_steps = result_data.get("timeline", ["💡 تم مطابقة الجذور واستنباط السياق العامي بنجاح."])

    except Exception as e:
        print(f"Error in Gemini selector: {e}")
        hejazi_sentences = [clean_text]
        najdi_sentences = [clean_text]
        timeline_steps = ["💡 حدثت مشكلة في التصفية السياقية، وتم عرض النص."]

    # الخطوة الثالثة: استخراج رموز CAPHI الحقيقية حصرياً من قاموس MADAR، أو توليدها عند عدم توفرها
    def get_real_caphi_for_sentence(sentence, dialect_code):
        words_in_sent = sentence.replace('؟', '').replace('!', '').replace('.', '').split()
        caphi_tokens = []
        
        for w in words_in_sent:
            norm_w = normalize_arabic(w)
            match = lexicon_df[(lexicon_df['Dialect'] == dialect_code) & (lexicon_df['CODA'].apply(normalize_arabic) == norm_w)]
            
            if not match.empty and pd.notna(match.iloc[0]['CAPHI']) and str(match.iloc[0]['CAPHI']).strip() != '':
                caphi_tokens.append(str(match.iloc[0]['CAPHI']).strip())
            else:
                caphi_tokens.append(fallback_pronunciation(w))
                
        return " ".join(caphi_tokens)

    hejazi_caphi_list = [format_pronunciation(get_real_caphi_for_sentence(s, 'JED')) for s in hejazi_sentences]
    najdi_caphi_list = [format_pronunciation(get_real_caphi_for_sentence(s, 'RIY')) for s in najdi_sentences]

    def generate_badge(sentences):
        count = len(sentences)
        if count == 2:
            return "<span style='background-color: #2a2a2a; color: #a0a0a0; padding: 4px 10px; border-radius: 6px; font-size: 13px; border: 1px solid #333;'>يتوفر خياران</span>"
        elif count == 3:
            return "<span style='background-color: #2a2a2a; color: #a0a0a0; padding: 4px 10px; border-radius: 6px; font-size: 13px; border: 1px solid #333;'>توفرت 3 خيارات</span>"
        elif count > 3:
            return f"<span style='background-color: #2a2a2a; color: #a0a0a0; padding: 4px 10px; border-radius: 6px; font-size: 13px; border: 1px solid #333;'>تتوفر {count} خيارات</span>"
        return ""

    unique_timeline = list(dict.fromkeys(timeline_steps))

    return {
        "hejazi_sentences": hejazi_sentences,
        "najdi_sentences": najdi_sentences,
        "hejazi_caphis": [[c] for c in hejazi_caphi_list],
        "najdi_caphis": [[c] for c in najdi_caphi_list],
        "hejazi_badge": generate_badge(hejazi_sentences),
        "najdi_badge": generate_badge(najdi_sentences),
        "timeline": unique_timeline
    }

# =====================================================================
# 2. دالة الترجمة العكسية (من العامية إلى الفصحى باستخدام الذكاء الاصطناعي)
# =====================================================================
def process_ammiya(text, lexicon_df=None, dialect_choice=None):
    clean_text = text.replace('؟', '').replace('!', '').replace('.', '').strip()
    
    try:
        prompt = f"""
        أنت خبير لغوي متخصص في اللهجات السعودية واللغة العربية الفصحى.
        قم بترجمة هذه العبارة العامية إلى لغة عربية فصحى سليمة تماماً:
        "{clean_text}"
        
        تعليمات هامة جداً للترجمة الدقيقة:
        1. حافظ على أصل الأفعال والكلمات بقدر الإمكان (مثلاً: الفعل المضارع يبقى مضارعاً ولا يتم تحويله لمصادر مجردة).
        2. عند شرح التغييرات، يجب أن يكون المقابل دقيقاً لكل كلمة على حدة دون دمج أدوات الاستفهام أو الحروف الزائدة (مثل "هل").
        3. اشرح التغييرات بالصيغة التالية تماماً:
        "💡 اللفظ العامي ((الكلمة_العامية)) يقابله بالفصحى كلمة ((الكلمة_الفصحى)) في هذا السياق."
        4. لا تذكر أي نصوص أو شروحات قبل أو بعد النتيجة النهائية، فقط أعد النتيجة بصيغة JSON.
        5. علامات الترقيم يجب أن تزيدها إذا لم تكن موجودة، ولكن اكتبها مرة واحدة دائماً.
        
        أريد النتيجة بصيغة JSON فقط، بدون أي نصوص أخرى قبلها أو بعدها، تحتوي على مفتاحين:
        1. "fusha": يحتوي على الترجمة الفصحى النهائية المباشرة والدقيقة.
        2. "changes": مصفوفة (List) تشرح التغييرات بالصيغة المحددة.
        
        مثال على المخرجات:
        {{
            "fusha": "هل يمكنك أن تأتي إلى الجامعة؟",
            "changes": [
                "💡 اللفظ العامي ((ممكن)) يقابله بالفصحى كلمة ((يمكنك)) في هذا السياق."
            ]
        }}
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash-lite',
                    contents=prompt,
                )
                break
            except Exception as api_e:
                if "503" in str(api_e) and attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    raise api_e
        
        response_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(response_text)
        
        fusha_result = data.get("fusha", clean_text)
        
        return {
            "fusha_sentences": [fusha_result],
            "timeline": data.get("changes", ["💡 تم تحليل السياق العامي واستنباط المعنى الفصيح."])
        }
        
    except Exception as e:
        print(f"\n🔥 خطأ في الخلفية: {str(e)}\n")
        return {
            "fusha_sentences": ["خطأ، في تحميل الملف!"],
            "timeline": ["💡 ((خطأ، في تحميل الملف!))"]
        }
