# 期刊库质检报告（OpenAlex 对拍 + PubMed 年发文量）

- 跑批时间：2026-10-31 07:23:18
- 总数：1498 本（config/journals_taxonomy.json v4.0.0 全量）
- PubMed 窗口：2025/10/01 – 2026/10/17（约 365 天，[ta] 按缩写匹配）
- 脚本：D:\tmp\journal_qc.py（支持断点续跑，已成功条目跳过）

## 汇总

- OpenAlex 命中：1289/1498（86%）；未命中 15 本
- 名字宽松比对不一致：61 本（见下）
- PubMed vol_365 取到：1498/1498；为 0 的 38 本
- 异常条目（含 error）：194 本（见异常清单）

### 名字不一致清单

| 我们 title | OpenAlex display_name | nlm_id |
|---|---|---|
| Nat Rev Clin Oncol | Nature Reviews Clinical Oncology | 101500077 |
| Nat Rev Cancer | Nature reviews. Cancer | 101124168 |
| Journal of Hematology Oncology | Journal of Hematology & Oncology | 101468937 |
| Nat Biotechnol | Nature Biotechnology | 9604648 |
| Nat Nanotechnol | Nature Nanotechnology | 101283273 |
| Nat Mach Intell | Nature Machine Intelligence | 101740243 |
| Cancer Communications | 癌症：英文版 | 101723675 |
| Nat Methods | Nature Methods | 101215604 |
| Nat Metab | Nature Metabolism | 101736592 |
| Nat Biomed Eng | Nature Biomedical Engineering | 101696896 |
| Sci Robot | Science Robotics | 101733136 |
| Cellular Molecular Immunology | Cellular and Molecular Immunology | 101242872 |
| Cell Host Microbe | Cell Host & Microbe | 101302316 |
| Lancet Glob Health | The Lancet Global Health | 101613665 |
| Trends Cancer | Trends in cancer | 101665956 |
| Science bulletin | 中国科学通报：英文版 | 101655530 |
| Lancet Planet Health | The Lancet Planetary Health | 101704339 |
| Nat Microbiol | Nature Microbiology | 101674869 |
| Experimental Hematology Oncology | Experimental Hematology and Oncology | 101590676 |
| JAMA pediatrics | Archives of Pediatrics and Adolescent Medicine | 101589544 |
| Mol Cell | Molecular Cell | 9802571 |
| Lancet Reg Health Eur | The Lancet Regional Health - Europe | 101777707 |
| J Clin Invest | Journal of Clinical Investigation | 7802877 |
| Cell Rep Med | Cell Reports Medicine | 101766894 |
| Lancet Child Adolesc Health | The Lancet Child & Adolescent Health | 101712925 |
| Cancer metastasis reviews | Cancer and Metastasis Reviews | 8605731 |
| Biochimica et biophysica acta. Reviews on cancer | Biochimica et Biophysica Acta (BBA) - Reviews on Cancer | 9806362 |
| CHEST | CHEST Journal | 0231335 |
| Lancet Reg Health West Pac | The Lancet Regional Health - Western Pacific | 101774968 |
| Lancet Reg Health Am | The Lancet Regional Health - Americas | 9918232503006676 |
| View | Open Research (University of Surrey) | 9918248414606676 |
| Sci Signal | Science Signaling | 101465400 |
| Lancet Reg Health Southeast Asia | The Lancet Regional Health - Southeast Asia | 9918419282806676 |
| Cancer Metabolism | Cancer & Metabolism | 101607582 |
| Cranio : the journal of craniomandibular practice | CRANIO® | 8609491 |
| Journal of integrative medicine | Journal of Chinese Integrative Medicine | 101603118 |
| JOURNAL OF DIGITAL IMAGING | Journal of Imaging Informatics in Medicine | 9100529 |
| Biochimica et biophysica acta. Molecular basis of disease | Biochimica et Biophysica Acta (BBA) - Molecular Basis of Disease | 101731730 |
| Journal of molecular medicine | Journal of molecular medecine | 7601745 |
| Biocybernetics and biomedical engineering | Journal of Applied Biomedicine | 8212385 |
| The International journal on drug policy | International Journal of Drug Policy | 9014759 |
| The patient | Patient | 101309314 |
| IEEE transactions on bio-medical engineering | IEEE Transactions on Biomedical Engineering | 0012737 |
| FASEB journal : official publication of the Federation of American Societies for Experimental Biology | The FASEB Journal | 8804484 |
| Environmental Epigenetics | Current Zoology | 101675941 |
| International Journal of Chronic Obstructive Pulmonary Disease | International Journal of COPD | 101273481 |
| Clinical and experimental pediatrics | Korean Journal of Pediatrics | 101761234 |
| Salud pública de México | Salud Pública de México | 0404371 |
| Canadian journal of anaesthesia = Journal canadien d'anesthésie | Canadian Journal of Anesthesia/Journal canadien d anesthésie | 8701709 |
| Pflügers Archiv : European journal of physiology | Pflügers Archiv - European Journal of Physiology | 0154720 |
| Ultraschall in der Medizin : Organ der Deutschen Gesellschaft für Ultraschall in der Medizin, [der] Österreichischen Gesellschaft für Ultraschall in der Medizin, [der] Schweizerischen Gesellschaft für Ultraschall in Medizin und Biologie | Ultraschall in der Medizin - European Journal of Ultrasound | 8303585 |
| Virchows Archiv : an international journal of pathology | Archiv für Pathologische Anatomie und Physiologie und für Klinische Medicin | 9423843 |
| COPD | COPD Journal of Chronic Obstructive Pulmonary Disease | 101211769 |
| SURGEON-JOURNAL OF THE ROYAL COLLEGES OF SURGEONS OF EDINBURGH AND IRELAND | The Surgeon | 101168329 |
| Pathology oncology research : POR | Pathology & Oncology Research | 9706087 |
| Burns : journal of the International Society for Burn Injuries | Burns | 8913178 |
| Anales de pediatria | Anales de Pediatría (English Edition) | 101765626 |
| Revista de saúde pública | Revista de Saúde Pública | 0135043 |
| Journal of the American Board of Family Medicine : JABFM | The Journal of the American Board of Family Medicine | 101256526 |
| LANGENBECKS ARCHIVES OF SURGERY | Langenbeck s Archives of Surgery | 9808285 |
| Nat Aging | Nature Aging | 101773306 |

### vol_365 最高 15 本

| title | vol_365 | tier |
|---|---|---|
| Trends in cell biology | 1933223 | B |
| Trends in pharmacological sciences | 1933223 | B |
| Trends in microbiology | 1933223 | B |
| Trends in biotechnology | 1933223 | B |
| Biomedical technology | 1933223 | B |
| Clinical gastroenterology and hepatology | 1933223 | A |
| Nucleic acids research | 1933223 | C |
| Physiology | 1933223 | B |
| Journal of biomedical science | 1933223 | B |
| Trends in genetics | 1933223 | B |
| Advanced healthcare materials | 1933223 | C |
| Clinical nuclear medicine | 1933223 | D |
| The thorax | 1933223 | B |
| Apoptosis | 1933223 | C |
| Clinical chemistry | 1933223 | C |

### OpenAlex 未命中清单

- Trends in cell biology（query_issn=0968-0039）
- Trends in pharmacological sciences（query_issn=0167-7691）
- Trends in microbiology（query_issn=0968-0055）
- Journal of biomedical science（query_issn=1075-2919）
- Trends in genetics（query_issn=0168-9479）
- Smart medicine（query_issn=2751-1863）
- Chinese medical journal pulmonary and critical care medicine（query_issn=2097-1982）
- The American journal of roentgenology（query_issn=0092-5381）
- Environmental health（query_issn=0013-9270）
- Cancer pathogenesis and therapy（query_issn=2097-2563）
- Transplantation and cellular therapy（query_issn=2666-6375）
- Primary care（query_issn=1460-4035）
- The journal of immunology（query_issn=1048-3233）
- Journal of epidemiology and population health（query_issn=2950-4368）
- Tobacco induced diseases（query_issn=2070-7266）

### 异常清单（error 非空）

- Biomedical technology（101649649）：openalex: no issn available
- Clinical gastroenterology and hepatology（101256639）：openalex: no issn available
- Nucleic acids research（9503949）：openalex: no issn available
- Physiology（9918696948706676）：openalex: no issn available
- Research; a journal of science and its applications（20120060R）：openalex: no issn available
- Advanced healthcare materials（101637470）：openalex: no issn available
- Clinical nuclear medicine（9918300288106676）：openalex: no issn available
- The thorax（9918333279706676）：openalex: no issn available
- Apoptosis（101515805）：openalex: no issn available
- Clinical chemistry（101773516）：openalex: no issn available
- Artificial intelligence in medicine（101750769）：openalex: no issn available
- Metabolic engineering（101136187）：openalex: no issn available
- Respirology（101688533）：openalex: no issn available
- Biochemical pharmacology（101570576）：openalex: no issn available
- Cancer gene therapy（101216499）：openalex: no issn available
- Genetics in medicine（101677464）：openalex: no issn available
- Pediatrics（9918917737106676）：openalex: no issn available
- Globalization and health（101748536）：openalex: no issn available
- Gene therapy（101770247）：openalex: no issn available
- The esophagus（101769674）：openalex: no issn available
- Cancer nanotechnology（9918957857106676）：openalex: no issn available
- Clinical epigenetics（101760774）：openalex: no issn available
- Mucosal immunology（101662200）：openalex: no issn available
- Immunology（9918822670206676）：openalex: no issn available
- Radiologia medica（0157417）：openalex: no issn available
- Pediatric critical care medicine（101637803）：openalex: no issn available
- Clinical pharmacology & therapeutics（0104217）：openalex: no issn available
- Biological procedures online（100963600）：openalex: no issn available
- Pharmacoeconomics（101184778）：openalex: no issn available
- Pediatric allergy and immunology（9001357A）：openalex: no issn available
- Molecular oncology（101601917）：openalex: no issn available
- Clinical immunology（9918715277706676）：openalex: no issn available
- Practical radiation oncology（101763277）：openalex: no issn available
- Biotechnology and bioengineering（101318085）：openalex: no issn available
- Xenotransplantation（101216546）：openalex: no issn available
- Histopathology（101721909）：openalex: no issn available
- Pediatric drugs（101253744）：openalex: no issn available
- Molecular immunology（101655909）：openalex: no issn available
- Clinical therapeutics（100958721）：openalex: no issn available
- Precision radiation oncology（101745613）：openalex: no issn available
- Metabolomics（9918266201506676）：openalex: no issn available
- Neuromuscular disorders（101653187）：openalex: no issn available
- Health technology assessment（9501929）：openalex: no issn available
- The AAPS journal（101223209）：openalex: no issn available
- Infection and immunity（101607390）：openalex: no issn available
- Patient safety in surgery（101645977）：openalex: no issn available
- Prenatal diagnosis（101745819）：openalex: no issn available
- Human molecular genetics（101758887）：openalex: no issn available
- Neurogastroenterology and motility（100935484）：openalex: no issn available
- Physica medica（2771069R）：openalex: no issn available
- Diagnostic and interventional radiology（101685441）：openalex: no issn available
- Chronic obstructive pulmonary diseases（101665139）：openalex: no issn available
- Total otolaryngology-head and neck surgery（101632092）：openalex: no issn available
- Pediatric radiology（101599275）：openalex: no issn available
- Infectious diseases（1302451）：openalex: no issn available
- Pediatric pulmonology（9918881164606676）：openalex: no issn available
- Lasers in surgery and medicine（8900180A）：openalex: no issn available
- Journal of research in nursing : JRN（101234311）：openalex[1744-9871]: HTTPError: HTTP Error 429: Too Many Requests
- Clinics in geriatric medicine（8603766）：openalex[0749-0690]: HTTPError: HTTP Error 429: Too Many Requests
- Scandinavian journal of caring sciences（8804206）：openalex[0283-9318]: HTTPError: HTTP Error 429: Too Many Requests
- Nursing & health sciences（100891857）：openalex[1441-0745]: HTTPError: HTTP Error 429: Too Many Requests
- Physiological reports（101607800）：openalex[2051-817X]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of community health（7600747）：openalex[0094-5145]: HTTPError: HTTP Error 429: Too Many Requests
- Developmental biology（101767543）：openalex: no issn available
- Belitung nursing journal（101685037）：openalex[2528-181X]: HTTPError: HTTP Error 429: Too Many Requests
- Annals of work exposures and health（101698454）：openalex[2398-7308]: HTTPError: HTTP Error 429: Too Many Requests
- Magnetic resonance imaging（8214883）：openalex[0730-725X]: HTTPError: HTTP Error 429: Too Many Requests
- World journal of pediatric surgery（101761337）：openalex[2096-6938]: HTTPError: HTTP Error 429: Too Many Requests
- Medicina del lavoro（101199932）：openalex: no issn available
- Telemedicine journal and e-health : the official journal of the American Telemedicine Association（100959949）：openalex[1530-5627]: HTTPError: HTTP Error 429: Too Many Requests
- Family medicine（8306464）：openalex[0742-3225]: HTTPError: HTTP Error 429: Too Many Requests
- Australian journal of general practice（101718099）：openalex[2208-794X]: HTTPError: HTTP Error 429: Too Many Requests
- Prehospital emergency care（101711985）：openalex: no issn available
- Primary health care research & development（100897390）：openalex[1463-4236]: HTTPError: HTTP Error 429: Too Many Requests
- Translational pediatrics（101649179）：openalex[2224-4344]: HTTPError: HTTP Error 429: Too Many Requests
- Annals of surgical treatment and research（101622895）：openalex[2288-6575]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of pediatric health care : official publication of National Association of Pediatric Nurse Associates & Practitioners（8709735）：openalex[0891-5245]: HTTPError: HTTP Error 429: Too Many Requests
- The Laryngoscope（8607378）：openalex[0023-852X]: HTTPError: HTTP Error 429: Too Many Requests
- Annals of the Royal College of Surgeons of England（7506860）：openalex[0035-8843]: HTTPError: HTTP Error 429: Too Many Requests
- Research in gerontological nursing（101392499）：openalex[1940-4921]: HTTPError: HTTP Error 429: Too Many Requests
- Allergy and asthma proceedings :（9603640）：openalex[1088-5412]: HTTPError: HTTP Error 429: Too Many Requests
- International journal of radiation biology（8809243）：openalex[0955-3002]: HTTPError: HTTP Error 429: Too Many Requests
- Pediatric investigation（101731527）：openalex[2096-3726]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of environmental pathology, toxicology and oncology : official organ of the International Society for Environmental Toxicology and Cancer（8501420）：openalex[0731-8898]: HTTPError: HTTP Error 429: Too Many Requests
- Pleura and peritoneum（101710063）：openalex[2364-7671]: HTTPError: HTTP Error 429: Too Many Requests
- JSLS : Journal of the Society of Laparoendoscopic Surgeons（100884618）：openalex[1086-8089]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of biological physics（0417731）：openalex[0092-0606]: HTTPError: HTTP Error 429: Too Many Requests
- Medical decision making（9918591185306676）：openalex: no issn available
- Family practice（8500875）：openalex[0263-2136]: HTTPError: HTTP Error 429: Too Many Requests
- Otolaryngologic clinics of North America（0144042）：openalex[0030-6665]: HTTPError: HTTP Error 429: Too Many Requests
- Laryngoscope investigative otolaryngology（101684963）：openalex[2378-8038]: HTTPError: HTTP Error 429: Too Many Requests
- Clinics in plastic surgery（0424767）：openalex[0094-1298]: HTTPError: HTTP Error 429: Too Many Requests
- International journal of emergency medicine（101469435）：openalex[1865-1372]: HTTPError: HTTP Error 429: Too Many Requests
- Clinical otolaryngology : official journal of ENT-UK ; official journal of Netherlands Society for Oto-Rhino-Laryngology & Cervico-Facial Surgery（101247023）：openalex[1749-4478]: HTTPError: HTTP Error 429: Too Many Requests
- Surgical oncology clinics of North America（9211789）：openalex[1055-3207]: HTTPError: HTTP Error 429: Too Many Requests
- Scandinavian journal of primary health care（8510679）：openalex[0281-3432]: HTTPError: HTTP Error 429: Too Many Requests
- Pathology international（9431380）：openalex[1320-5463]: HTTPError: HTTP Error 429: Too Many Requests
- Plastic and reconstructive surgery. Global open（101622231）：openalex[2169-7574]: HTTPError: HTTP Error 429: Too Many Requests
- Medical care（0230027）：openalex[0025-7079]: HTTPError: HTTP Error 429: Too Many Requests
- Pediatric reports（101551542）：openalex[2036-749X]: HTTPError: HTTP Error 429: Too Many Requests
- Acta anaesthesiologica Scandinavica（0370270）：openalex[0001-5172]: HTTPError: HTTP Error 429: Too Many Requests
- Frontiers in surgery（101645127）：openalex[2296-875X]: HTTPError: HTTP Error 429: Too Many Requests
- Physiology international（101696724）：openalex[2498-602X]: HTTPError: HTTP Error 429: Too Many Requests
- Memórias do Instituto Oswaldo Cruz（7502619）：openalex[0074-0276]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of transcultural nursing : official journal of the Transcultural Nursing Society（9001407）：openalex[1043-6596]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of child health care : for professionals working with children in the hospital and community（9806360）：openalex[1367-4935]: HTTPError: HTTP Error 429: Too Many Requests
- Asian Pacific journal of tropical biomedicine（101557706）：openalex[2221-1691]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of community health nursing（8411341）：openalex[0737-0016]: HTTPError: HTTP Error 429: Too Many Requests
- The American journal of tropical medicine and hygiene（0370507）：openalex[0002-9637]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of surgical oncology（101764928）：openalex[2674-3000]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of burn care & research : official publication of the American Burn Association（101262774）：openalex[1559-047X]: HTTPError: HTTP Error 429: Too Many Requests
- Auris, nasus, larynx（7708170）：openalex[0385-8146]: HTTPError: HTTP Error 429: Too Many Requests
- Brazilian journal of otorhinolaryngology（101207337）：openalex[1808-8694]: HTTPError: HTTP Error 429: Too Many Requests
- Current pediatrics reports（101600850）：openalex[2167-4841]: HTTPError: HTTP Error 429: Too Many Requests
- American journal of otolaryngology（8000029）：openalex[0196-0709]: HTTPError: HTTP Error 429: Too Many Requests
- Acta paediatrica（9205968）：openalex[0803-5253]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of the American College of Emergency Physicians open（101764779）：openalex[2688-1152]: HTTPError: HTTP Error 429: Too Many Requests
- Human mutation（9215429）：openalex[1059-7794]: HTTPError: HTTP Error 429: Too Many Requests
- European journal of pediatric surgery : official journal of Austrian Association of Pediatric Surgery ... [et al] = Zeitschrift für Kinderchirurgie（9105263）：openalex[0939-7248]: HTTPError: HTTP Error 429: Too Many Requests
- JPRAS open（101680420）：openalex[2352-5878]: HTTPError: HTTP Error 429: Too Many Requests
- Japan journal of nursing science : JJNS（101227890）：openalex[1742-7932]: HTTPError: HTTP Error 429: Too Many Requests
- Clinical transplantation（100949033）：openalex: no issn available
- Local and regional anesthesia（101566276）：openalex[1178-7112]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of hospital medicine（101271025）：openalex[1553-5592]: HTTPError: HTTP Error 429: Too Many Requests
- African journal of primary health care & family medicine（101520860）：openalex[2071-2928]: HTTPError: HTTP Error 429: Too Many Requests
- Anatomical science international（101154140）：openalex[1447-6959]: HTTPError: HTTP Error 429: Too Many Requests
- Open access emergency medicine : OAEM（101570796）：openalex[1179-1500]: HTTPError: HTTP Error 429: Too Many Requests
- Clinical medicine insights. Pediatrics（101595023）：openalex[1179-5565]: HTTPError: HTTP Error 429: Too Many Requests
- Fetal diagnosis and therapy（9107463）：openalex[1015-3837]: HTTPError: HTTP Error 429: Too Many Requests
- European annals of otorhinolaryngology, head and neck diseases（101531465）：openalex[1879-7296]: HTTPError: HTTP Error 429: Too Many Requests
- OTO open（101717942）：openalex[2473-974X]: HTTPError: HTTP Error 429: Too Many Requests
- Advances in neonatal care : official journal of the National Association of Neonatal Nurses（101125644）：openalex[1536-0903]: HTTPError: HTTP Error 429: Too Many Requests
- Emergency medicine clinics of North America（8219565）：openalex[0733-8627]: HTTPError: HTTP Error 429: Too Many Requests
- International journal of pediatric otorhinolaryngology（8003603）：openalex[0165-5876]: HTTPError: HTTP Error 429: Too Many Requests
- Revista paulista de pediatria : orgão oficial da Sociedade de Pediatria de São Paulo（9109353）：openalex[0103-0582]: HTTPError: HTTP Error 429: Too Many Requests
- Annals of plastic surgery（7805336）：openalex[0148-7043]: HTTPError: HTTP Error 429: Too Many Requests
- Surgery open science（101768812）：openalex[2589-8450]: HTTPError: HTTP Error 429: Too Many Requests
- The Physician and sportsmedicine（0427461）：openalex[0091-3847]: HTTPError: HTTP Error 429: Too Many Requests
- Physiotherapy theory and practice（9015520）：openalex[0959-3985]: HTTPError: HTTP Error 429: Too Many Requests
- The Journal of emergency medicine（8412174）：openalex[0736-4679]: HTTPError: HTTP Error 429: Too Many Requests
- Acta cirúrgica brasileira（9103983）：openalex[0102-8650]: HTTPError: HTTP Error 429: Too Many Requests
- Congenital anomalies（9306292）：openalex[0914-3505]: HTTPError: HTTP Error 429: Too Many Requests
- Emergency medicine international（101567070）：openalex[2090-2840]: HTTPError: HTTP Error 429: Too Many Requests
- Translational research in anatomy（101736190）：openalex[2214-854X]: HTTPError: HTTP Error 429: Too Many Requests
- Morphologie : bulletin de l'Association des anatomistes（9814314）：openalex[1286-0115]: HTTPError: HTTP Error 429: Too Many Requests
- Indian pediatrics（2985062R）：openalex[0019-6061]: HTTPError: HTTP Error 429: Too Many Requests
- World journal of otorhinolaryngology（101634993）：openalex[2218-6247]: HTTPError: HTTP Error 429: Too Many Requests
- Clinical nursing research（9208508）：openalex[1054-7738]: HTTPError: HTTP Error 429: Too Many Requests
- Emergency medicine Australasia : EMA（101199824）：openalex[1742-6731]: HTTPError: HTTP Error 429: Too Many Requests
- Archives de pédiatrie : organe officiel de la Sociéte française de pédiatrie（9421356）：openalex[0929-693X]: HTTPError: HTTP Error 429: Too Many Requests
- Surgical and radiologic anatomy : SRA（8608029）：openalex[0930-1038]: HTTPError: HTTP Error 429: Too Many Requests
- Current transplantation reports（101624626）：openalex[2196-3029]: HTTPError: HTTP Error 429: Too Many Requests
- Journal of transplantation（101519118）：openalex[2090-0007]: HTTPError: HTTP Error 429: Too Many Requests
- Anesthesiology research and practice（101532982）：openalex[1687-6962]: HTTPError: HTTP Error 429: Too Many Requests
- Hong Kong physiotherapy journal : official publication of the Hong Kong Physiotherapy Association Limited = Wu li chih liao（100908968）：openalex[1013-7025]: HTTPError: HTTP Error 429: Too Many Requests
- Pediatrics in review（8103046）：openalex[0191-9601]: HTTPError: HTTP Error 429: Too Many Requests
- Nepal journal of epidemiology（101583212）：openalex[2091-0800]: HTTPError: HTTP Error 429: Too Many Requests
- Folia morphologica（0010076）：openalex[0015-5640]: HTTPError: HTTP Error 429: Too Many Requests
- Current opinion in otolaryngology & head and neck surgery（9417024）：openalex[1068-9508]: HTTPError: HTTP Error 429: Too Many Requests
- American journal of perinatology（8405212）：openalex[0735-1631]: HTTPError: HTTP Error 429: Too Many Requests
- Current otorhinolaryngology reports（101600851）：openalex[2167-583X]: HTTPError: HTTP Error 429: Too Many Requests
- The Nursing clinics of North America（0042033）：openalex[0029-6465]: HTTPError: HTTP Error 429: Too Many Requests
- Acta oto-laryngologica（0370354）：openalex[0001-6489]: HTTPError: HTTP Error 429: Too Many Requests
- The Annals of otology, rhinology, and laryngology（0407300）：openalex[0003-4894]: HTTPError: HTTP Error 429: Too Many Requests
- Applied immunohistochemistry & molecular morphology : AIMM（100888796）：openalex[1541-2016]: HTTPError: HTTP Error 429: Too Many Requests
- Critical care nursing clinics of North America（8912620）：openalex[0899-5885]: HTTPError: HTTP Error 429: Too Many Requests
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available
- （）：openalex: no issn available

## 阵地周报

### 阵地周报（近 7 天 · 锚 2026-10-31）

- 口径：命中率＝命中篇数/在册数（每刊产出，年检按此从低到高裁）；上榜率＝命中篇数/近窗入库总篇数。
- 类目：1 胸部肿瘤与胸外科｜2 肿瘤临床｜3 外科与重症医学｜4 影像、病理与检验｜5 感染与免疫｜6 邻科临床｜7 公共卫生与人群健康｜8 基础与转化医学｜9 综合医学与多学科｜10 医学AI与数字医学｜待定=待审定。

| 类目 | 在册数 | 命中篇数 | 命中率 | 上榜率 |
|---|---|---|---|---|
| 1 | 62 | 45 | 72.58% | 4.01% |
| 10 | 48 | 14 | 29.17% | 1.25% |
| 2 | 126 | 97 | 76.98% | 8.65% |
| 3 | 130 | 23 | 17.69% | 2.05% |
| 4 | 94 | 36 | 38.30% | 3.21% |
| 5 | 196 | 116 | 59.18% | 10.34% |
| 6 | 148 | 107 | 72.30% | 9.54% |
| 7 | 252 | 106 | 42.06% | 9.45% |
| 8 | 386 | 358 | 92.75% | 31.91% |
| 9 | 55 | 166 | 301.82% | 14.80% |
| 待定 | 1 | 54 | 5400.00% | 4.81% |

- 信噪观察（10 类）：在册 48 本仅命中 14 篇（命中率 29.17%），低产出属预期（默认折叠类）；年检按命中率裁汰。
- 信噪观察（8 类）：在册 386 本仅命中 358 篇（命中率 92.75%），低产出属预期（默认折叠类）；年检按命中率裁汰。

### 期刊目录健康（data/journal_health.json）

- 红档（≥100 天未命中，疑改名/停刊/检索键失效，人工核）：0 本
- 黄档（45–99 天，低频刊/季刊可能正常）：0 本
- 绿档（<45 天）：1506 本
- 结论：全部健康。
