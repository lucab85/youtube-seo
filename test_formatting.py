#!/usr/bin/env python3
"""Test the description formatting."""

import re

def format_description(description: str) -> str:
    """Add proper line breaks to description."""
    if '\n' in description:
        return description
    
    formatted = description
    
    # 1. Add line break after each bullet point
    formatted = re.sub(r'(• [^•]+?)\s+(?=•)', r'\1\n', formatted)
    
    # 2. Add double line break before "What You'll Learn:"
    formatted = re.sub(r'([.!?])\s+(What You\'ll Learn:)', r'\1\n\n\2', formatted)
    
    # 3. Add line break after "What You'll Learn:" header
    formatted = re.sub(r'(What You\'ll Learn:)\s+(?=•)', r'\1\n', formatted)
    
    # 4. Add double line break after last bullet point before timestamps
    formatted = re.sub(r'(• [^•]+?)\s+(\d+:\d+)', r'\1\n\n\2', formatted)
    
    # 5. Add line break after each timestamp line
    formatted = re.sub(r'(\d+:\d+ [^\n]+?)\s+(?=\d+:\d+)', r'\1\n', formatted)
    
    # 6. Add double line break after last timestamp
    formatted = re.sub(r'(\d+:\d+ [^\n]+?)\s+([A-Z][a-z]+ (session|presentation|talk|video))', r'\1\n\n\2', formatted)
    
    # 7. Add double line break before major sections
    section_headers = [
        'This session', 'This presentation', 'This video', 'This talk',
        'Key Insights', 'Key Takeaways', 'Takeaways:',
        'Additional Resources:', 'Resources:',
        'About This Channel:', 'About the Channel:',
        'If you enjoyed', 'If you found this video'
    ]
    for header in section_headers:
        formatted = re.sub(rf'([.!?])\s+({re.escape(header)})', r'\1\n\n\2', formatted, flags=re.IGNORECASE)
    
    # 8. Add line break after section headers with colon
    formatted = re.sub(r'(Key Insights[^:]*:)\s+(?=•)', r'\1\n', formatted)
    formatted = re.sub(r'(Takeaways[^:]*:)\s+(?=•)', r'\1\n', formatted)
    
    # 9. Break up long paragraphs
    sections = formatted.split('\n\n')
    formatted_sections = []
    for section in sections:
        if len(section) > 300 and '. ' in section and not section.strip().startswith('•'):
            sentences = section.split('. ')
            new_section = []
            current_para = []
            current_length = 0
            
            for i, sentence in enumerate(sentences):
                sentence_with_period = sentence if i == len(sentences) - 1 else sentence + '.'
                current_para.append(sentence_with_period)
                current_length += len(sentence_with_period)
                
                if (len(current_para) >= 2 and current_length > 150) or current_length > 250:
                    new_section.append(' '.join(current_para))
                    current_para = []
                    current_length = 0
            
            if current_para:
                new_section.append(' '.join(current_para))
            
            formatted_sections.append('\n\n'.join(new_section))
        else:
            formatted_sections.append(section)
    
    formatted = '\n\n'.join(formatted_sections)
    
    # 10. Clean up excessive line breaks
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    return formatted.strip()

# Test with your actual description
test_desc = """Discover how Level is using main topic for observability to power its AI-driven application platform! See how ClickHouse enables them to analyze vast amounts of data and gain critical insights. This video dives into Level's observability strategy, showcasing how they leverage ClickHouse to monitor and optimize their AI-powered platform. You'll learn about their real-world use cases, the challenges they face, and the solutions they've implemented. What You'll Learn: • How Level uses ClickHouse for observability. • The architecture of their data pipeline for analytics. • How ClickHouse helps them analyze user behavior and application performance. 0:00 Introduction 2:15 Observability Use Case 5:30 Web Analytics Use Case 9:20 Security Scanning 11:35 Moving Fast with Data 13:45 ClickHouse and AI 15:00 Hiring This presentation explores the two major use cases of ClickHouse at Level: observability and web analytics. For observability, the presenter describes how they use ClickHouse to monitor their microservices, Kubernetes clusters, and other infrastructure components. They discuss the challenges of analyzing data from a highly stochastic system and how ClickHouse helps them understand application behavior and troubleshoot issues. The presentation also discusses how level uses AI and Clickhouse to improve their cybersecurity by scanning their applications daily for vulnerabilities. The presenter also covers Level's use of ClickHouse for web analytics, explaining how they collect and analyze data from millions of web apps. He highlights the ease of setting up the system and the impressive query performance they've achieved with minimal engineering effort. He mentions response times of only 50 milliseconds for queries regarding visit, view, session, and boundaries information, gathered from numerous devices. Key Insights & Takeaways: • ClickHouse enables real-time observability for complex AI-powered applications. • It empowers data-driven decision-making across engineering teams. • ClickHouse can be easily implemented for web analytics with impressive results. • Kickstart the Harmony between AI and Engineers, level makes this possible. About This Channel: Luca Berton covers topics like ClickHouse, database architecture, observability, and other data-related topics. Subscribe to learn more! If you enjoyed this video, please give it a like, leave a comment with your thoughts, and subscribe to the channel for more content. Also, hit the notification bell to be alerted when we upload the next video!"""

formatted = format_description(test_desc)

print("=" * 80)
print("FORMATTED DESCRIPTION WITH LINE BREAKS:")
print("=" * 80)
print(formatted)
print()
print("=" * 80)
print("LINE BREAK COUNT:", formatted.count('\n'))
print("=" * 80)
