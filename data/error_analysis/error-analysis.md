# Error Analysis: UADReview.md Processing Results

## Summary Statistics
- **Total Citations**: 418
- **Successful Corrections**: 336 (80.4%)
- **Failed Extractions**: 82 (19.6%)

## Error Categories

### 1. Publisher Access Restrictions (Paywalls/Blocking) - ~65% of errors

#### Emerald Publishing (Multiple 403 Forbidden)
- `doi.org/10.1108/14635780310483656` → 403 Forbidden (emerald.com)
- `doi.org/10.1108/JPIF-09-2020-0101` → 403 Forbidden (emerald.com)
- `doi.org/10.1108/02637470910998465` → 403 Forbidden (emerald.com)
- `doi.org/10.1108/14635780710776654` → 404 Not Found
- `doi.org/10.1108/jpif-01-2024-0001` → 403 Forbidden (emerald.com)
- `doi.org/10.1108/jerer-05-2024-0035` → 403 Forbidden (emerald.com)

#### MDPI Publishing (Blocking despite workaround attempts)
- `mdpi.com/2227-7080/12/8/128` → 403 Forbidden
- `doi.org/10.3390/technologies12080128` → 403 Forbidden (redirects to MDPI)

#### Other Academic Publishers
- `doi.org/10.1073/pnas.2100050118` → 403 Forbidden (pnas.org)
- `doi.org/10.1145/3503250` → 403 Forbidden (dl.acm.org)
- `doi.org/10.1080/21670811.2014.976411` → 403 Forbidden (tandfonline.com)

### 2. Malformed URLs/Citations - ~15% of errors

#### Invalid Markdown Link Formats
- `[16` → Incomplete markdown link
- `[37` → Incomplete markdown link
- `[59` → Incomplete markdown link
- `[62` → Incomplete markdown link
- `[66` → Incomplete markdown link
- `[74` → Incomplete markdown link
- `[80` → Incomplete markdown link
- `[116` → Incomplete markdown link
- `[158` → Incomplete markdown link
- `[163` → Incomplete markdown link

#### Bare Numbers as Citations
- `39` → Processed as citation text
- `54` → Processed as citation text
- `60` → Processed as citation text
- `67` → Processed as citation text
- `75` → Processed as citation text
- `77` → Processed as citation text
- `89` → Processed as citation text
- `91` → Processed as citation text
- `94` → Processed as citation text
- `106` → Processed as citation text
- `112` → Processed as citation text
- `114` → Processed as citation text
- `117` → Processed as citation text
- `155` → Processed as citation text
- `159` → Processed as citation text
- `185` → Processed as citation text

#### Malformed DOI URLs
- `doi.org/10.1016/0167-2789\(90\` → Escaped characters in URL
- `doi.org/10.1016/S0169-7218\(11\` → Escaped characters in URL

### 3. Institutional/Non-Academic Sources - ~15% of errors

#### Government/Institutional Sites
- `Freddie Mac, 2024` → Multiple instances, no structured metadata
- `Columbia University, 2024` → Generic institutional content
- `Brookings Institution, 2008` → Think tank publication
- `DIFI (2025)` → Government/regulatory body
- `MIT News (2025)` → News article, not academic paper

#### Corporate/Commercial Sites
- `alphacam.at` → Commercial website
- `Digital Initiatives at the Grad Center, 2025` → Institutional repository

#### News/Blog Content
- `arXiv, 2024` → Reference to arXiv platform, not specific paper
- `arXiv, 2025` → Reference to arXiv platform, not specific paper
- `CEUR-WS.org, 2024` → Conference proceedings website

### 4. PDF Processing Issues - ~5% of errors

#### Generic/Incomplete Extractions
- Multiple PDFs returning generic titles like "Unknown", "Open", "Learning"
- Author extraction often incomplete or incorrect
- High incidence of `#GUESSED` tags indicating low confidence

#### Specific PDF Problems
- `GOV.UK, 2024` → PDF processing gave "Bidanset" (likely filename)
- `The Appraisal of an Appraisal Company (2023)` → Gave "Pomykacz" (partial author)
- `IAAO, 2024` → Gave "Learning PDF #GUESSED" (generic title)

## Most Problematic Publishers/Domains

| Publisher/Domain | Error Count | Primary Issue |
|------------------|-------------|---------------|
| Emerald (emerald.com) | 6+ | 403 Forbidden |
| MDPI (mdpi.com) | 2+ | 403 Forbidden |
| Institutional URLs | 10+ | No structured metadata |
| Malformed Citations | 20+ | Invalid markdown syntax |
| PDF Documents | 15+ | Poor metadata extraction |

## Recommendations

### High Priority Fixes
1. **Enhanced Publisher Support**: Add more robust extractors for paywalled publishers
2. **URL Validation**: Pre-validate markdown links before processing
3. **Citation Format Cleanup**: Better parsing of malformed citations
4. **PDF Processing**: Improve title/author extraction algorithms

### Medium Priority Improvements
1. **Institutional Content**: Add extractors for government/news sites
2. **Backup Data Sources**: Implement CrossRef/DBLP fallbacks
3. **Error Classification**: Better categorization of failure types
4. **User Guidance**: Suggest fixes for common citation format errors

### Cache Performance
- Excellent performance with many "CACHE" hits observed
- System handled 418 citations efficiently
- No cache-related errors encountered
