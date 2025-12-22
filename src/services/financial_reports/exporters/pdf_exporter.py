"""PDF格式导出器。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from config import DATA_DIR
from models.financial_schemas import BalanceSheetData, CashFlowData, IncomeStatementData, ReportConfig

logger = logging.getLogger(__name__)


class PDFExporter:
    """PDF格式导出器。"""

    def __init__(self) -> None:
        """初始化PDF导出器。"""
        self.reports_dir = DATA_DIR / "reports" / "financial"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self._chinese_font_registered = False
        self._chinese_font_name = None

    def _register_chinese_font(self) -> Optional[str]:
        """注册中文字体。
        
        Returns:
            Optional[str]: 注册的字体名称，失败返回None
        """
        if self._chinese_font_registered and self._chinese_font_name:
            return self._chinese_font_name
        
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import platform
            import os
            
            # 常见的中文字体路径
            font_paths = []
            
            system = platform.system()
            if system == "Windows":
                # Windows字体路径
                windows_font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
                font_paths.extend([
                    os.path.join(windows_font_dir, 'simsun.ttc'),  # 宋体
                    os.path.join(windows_font_dir, 'simhei.ttf'),  # 黑体
                    os.path.join(windows_font_dir, 'msyh.ttc'),    # 微软雅黑
                    os.path.join(windows_font_dir, 'simkai.ttf'), # 楷体
                ])
            elif system == "Darwin":  # macOS
                font_paths.extend([
                    '/System/Library/Fonts/STHeiti Light.ttc',
                    '/System/Library/Fonts/PingFang.ttc',
                    '/Library/Fonts/Arial Unicode.ttf',
                ])
            elif system == "Linux":
                font_paths.extend([
                    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                    '/usr/share/fonts/truetype/arphic/uming.ttc',
                ])
            
            # 尝试注册字体
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font_name = 'ChineseFont'
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        logger.info(f"成功注册中文字体: {font_path} -> {font_name}")
                        self._chinese_font_registered = True
                        self._chinese_font_name = font_name
                        return font_name
                    except Exception as e:
                        logger.warning(f"注册字体失败 {font_path}: {e}")
                        continue
            
            logger.warning("未找到可用的中文字体，将使用默认字体（中文可能显示为方块）")
            return None
            
        except ImportError:
            logger.warning("reportlab未安装，无法注册中文字体")
            return None
        except Exception as e:
            logger.warning(f"注册中文字体时发生错误: {e}")
            return None

    def _markdown_to_pdf(self, markdown_content: str, output_path: Path) -> bool:
        """将Markdown内容转换为PDF文件。
        
        Args:
            markdown_content: Markdown内容
            output_path: 输出PDF文件路径
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"开始将Markdown转换为PDF: {output_path}")
        
        if not markdown_content or not markdown_content.strip():
            logger.error("Markdown内容为空，无法生成PDF")
            return False
        
        try:
            # 尝试使用weasyprint
            try:
                logger.debug("尝试使用weasyprint生成PDF")
                import markdown
                from weasyprint import HTML, CSS
                from weasyprint.text.fonts import FontConfiguration
                
                logger.debug("weasyprint库导入成功，开始转换Markdown到HTML")
                # 将markdown转换为HTML
                html_content = markdown.markdown(
                    markdown_content,
                    extensions=['tables', 'fenced_code']
                )
                
                logger.debug("HTML转换完成，添加样式")
                # 添加基本样式
                html_with_style = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            font-family: "SimSun", "宋体", Arial, sans-serif;
                            font-size: 12pt;
                            line-height: 1.6;
                            margin: 20px;
                        }}
                        h1 {{
                            font-size: 18pt;
                            font-weight: bold;
                            margin-top: 20px;
                            margin-bottom: 10px;
                        }}
                        h2 {{
                            font-size: 16pt;
                            font-weight: bold;
                            margin-top: 15px;
                            margin-bottom: 8px;
                        }}
                        h3 {{
                            font-size: 14pt;
                            font-weight: bold;
                            margin-top: 12px;
                            margin-bottom: 6px;
                        }}
                        table {{
                            border-collapse: collapse;
                            width: 100%;
                            margin: 10px 0;
                        }}
                        th, td {{
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: left;
                        }}
                        th {{
                            background-color: #f2f2f2;
                            font-weight: bold;
                        }}
                        p {{
                            margin: 5px 0;
                        }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                
                logger.debug("开始使用weasyprint生成PDF文件")
                # 生成PDF
                font_config = FontConfiguration()
                HTML(string=html_with_style).write_pdf(
                    str(output_path),
                    font_config=font_config
                )
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"PDF已成功生成（使用weasyprint）: {output_path}, 大小: {output_path.stat().st_size} 字节")
                    return True
                else:
                    logger.warning(f"PDF文件生成但文件不存在或为空: {output_path}")
                    return False
                
            except ImportError as e:
                logger.warning(f"weasyprint未安装或导入失败: {e}，尝试使用reportlab")
            except Exception as e:
                logger.warning(f"weasyprint生成PDF失败: {e}，尝试使用reportlab回退方案", exc_info=True)
            
            # 如果没有weasyprint或weasyprint失败，尝试使用reportlab
            try:
                logger.debug("尝试使用reportlab生成PDF")
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib import colors
                import re
                
                logger.debug("reportlab库导入成功，开始创建PDF文档")
                # 创建PDF文档
                doc = SimpleDocTemplate(str(output_path), pagesize=A4)
                story = []
                styles = getSampleStyleSheet()
                
                # 自定义样式
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    textColor=colors.black,
                    spaceAfter=12,
                )
                
                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=14,
                    textColor=colors.black,
                    spaceAfter=8,
                )
                
                logger.debug("开始解析Markdown内容")
                # 解析markdown内容
                lines = markdown_content.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    if not line:
                        story.append(Spacer(1, 6))
                        i += 1
                        continue
                    
                    # 处理标题
                    if line.startswith('# '):
                        text = line[2:].strip()
                        story.append(Paragraph(text, title_style))
                        story.append(Spacer(1, 12))
                    elif line.startswith('## '):
                        text = line[3:].strip()
                        story.append(Paragraph(text, heading_style))
                        story.append(Spacer(1, 8))
                    elif line.startswith('### '):
                        text = line[4:].strip()
                        story.append(Paragraph(text, styles['Heading3']))
                        story.append(Spacer(1, 6))
                    # 处理表格
                    elif line.startswith('|'):
                        # 收集表格行
                        table_rows = []
                        while i < len(lines) and lines[i].strip().startswith('|'):
                            row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
                            table_rows.append(row)
                            i += 1
                        
                        if len(table_rows) > 1:
                            # 第一行是表头
                            data = table_rows
                            table = Table(data)
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 10),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ]))
                            story.append(table)
                            story.append(Spacer(1, 12))
                        continue
                    # 处理普通文本
                    else:
                        # 移除markdown格式
                        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                        story.append(Paragraph(text, styles['Normal']))
                    
                    i += 1
                
                logger.debug("开始构建PDF文档")
                # 构建PDF
                doc.build(story)
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"PDF已成功生成（使用reportlab）: {output_path}, 大小: {output_path.stat().st_size} 字节")
                    return True
                else:
                    logger.error(f"PDF文件生成但文件不存在或为空: {output_path}")
                    return False
                    
            except ImportError as e:
                logger.error(f"未安装reportlab库，无法生成PDF: {e}", exc_info=True)
                return False
            except Exception as e:
                logger.exception(f"reportlab生成PDF失败: {e}")
                return False
                    
        except Exception as e:
            logger.exception(f"PDF生成过程发生未预期的错误: {e}")
            return False

    def export_balance_sheet(
        self, 
        balance_sheet_data: BalanceSheetData, 
        config: ReportConfig,
        ai_analysis: Optional[str] = None
    ) -> Optional[str]:
        """导出资产负债表为PDF文件。
        
        Args:
            balance_sheet_data: 资产负债表数据结构
            config: 报表配置
            
        Returns:
            Optional[str]: PDF文件路径，失败返回None
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = self.reports_dir / f"balance_sheet_{timestamp}.pdf"
        
        logger.info(f"开始生成资产负债表PDF: {pdf_path}")
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm, cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib import colors
            
            logger.debug("reportlab库导入成功")
            
            # 注册中文字体
            chinese_font = self._register_chinese_font()
            if chinese_font:
                logger.debug(f"使用中文字体: {chinese_font}")
            
            # 创建PDF文档
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            story = []
            styles = getSampleStyleSheet()
            
            # 根据是否注册了中文字体来选择字体名称
            header_font_name = chinese_font if chinese_font else 'Helvetica-Bold'
            normal_font_name = chinese_font if chinese_font else 'Helvetica'
            
            # 定义样式
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.black,
                spaceAfter=12,
                alignment=1,  # 居中
                fontName=header_font_name,
            )
            
            header_style = ParagraphStyle(
                'Header',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                spaceAfter=6,
                fontName=normal_font_name,
            )
            
            table_header_style = ParagraphStyle(
                'TableHeader',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                fontName=header_font_name,
            )
            
            table_normal_style = ParagraphStyle(
                'TableNormal',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.black,
                fontName=normal_font_name,
            )
            
            table_total_style = ParagraphStyle(
                'TableTotal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                fontName=header_font_name,
            )
            
            # 标题
            title = "资产负债表"
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 6))
            
            # 公司名称和报表日期
            if balance_sheet_data.company_name:
                story.append(Paragraph(f"公司名称：{balance_sheet_data.company_name}", header_style))
            report_date_str = balance_sheet_data.report_date.strftime('%Y年%m月%d日')
            story.append(Paragraph(f"报表日期：{report_date_str}", header_style))
            story.append(Paragraph(f"币种：{config.currency}", header_style))
            story.append(Spacer(1, 12))
            
            # 构建表格数据
            table_data = []
            
            # 表头
            table_data.append([
                Paragraph("项目", table_header_style),
                Paragraph("金额", table_header_style),
            ])
            
            # 资产部分
            table_data.append([
                Paragraph("<b>资产</b>", table_header_style),
                Paragraph("", table_normal_style),
            ])
            
            # 处理资产项目
            for asset_item in balance_sheet_data.assets:
                # 主分类
                if asset_item.sub_items:
                    table_data.append([
                        Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{asset_item.name}", table_normal_style),
                        Paragraph("", table_normal_style),
                    ])
                    # 子项目
                    for sub_item in asset_item.sub_items:
                        amount_str = f"{sub_item.amount:,.2f}" if sub_item.amount != 0 else ""
                        table_data.append([
                            Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item.name}", table_normal_style),
                            Paragraph(amount_str, table_normal_style),
                        ])
                    # 小计
                    amount_str = f"{asset_item.amount:,.2f}" if asset_item.amount != 0 else ""
                    table_data.append([
                        Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{asset_item.name}小计", table_total_style),
                        Paragraph(amount_str, table_total_style),
                    ])
                else:
                    amount_str = f"{asset_item.amount:,.2f}" if asset_item.amount != 0 else ""
                    table_data.append([
                        Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{asset_item.name}", table_normal_style),
                        Paragraph(amount_str, table_normal_style),
                    ])
            
            # 资产合计
            table_data.append([
                Paragraph("<b>资产合计</b>", table_total_style),
                Paragraph(f"{balance_sheet_data.total_assets:,.2f}", table_total_style),
            ])
            
            # 负债部分
            table_data.append([
                Paragraph("<b>负债</b>", table_header_style),
                Paragraph("", table_normal_style),
            ])
            
            # 处理负债项目
            for liability_item in balance_sheet_data.liabilities:
                # 主分类
                if liability_item.sub_items:
                    table_data.append([
                        Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{liability_item.name}", table_normal_style),
                        Paragraph("", table_normal_style),
                    ])
                    # 子项目
                    for sub_item in liability_item.sub_items:
                        amount_str = f"{sub_item.amount:,.2f}" if sub_item.amount != 0 else ""
                        table_data.append([
                            Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item.name}", table_normal_style),
                            Paragraph(amount_str, table_normal_style),
                        ])
                    # 小计
                    amount_str = f"{liability_item.amount:,.2f}" if liability_item.amount != 0 else ""
                    table_data.append([
                        Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{liability_item.name}小计", table_total_style),
                        Paragraph(amount_str, table_total_style),
                    ])
                else:
                    amount_str = f"{liability_item.amount:,.2f}" if liability_item.amount != 0 else ""
                    table_data.append([
                        Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{liability_item.name}", table_normal_style),
                        Paragraph(amount_str, table_normal_style),
                    ])
            
            # 负债合计
            table_data.append([
                Paragraph("<b>负债合计</b>", table_total_style),
                Paragraph(f"{balance_sheet_data.total_liabilities:,.2f}", table_total_style),
            ])
            
            # 所有者权益部分
            table_data.append([
                Paragraph("<b>所有者权益</b>", table_header_style),
                Paragraph("", table_normal_style),
            ])
            
            # 处理所有者权益项目
            for equity_item in balance_sheet_data.equity:
                amount_str = f"{equity_item.amount:,.2f}" if equity_item.amount != 0 else ""
                table_data.append([
                    Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{equity_item.name}", table_normal_style),
                    Paragraph(amount_str, table_normal_style),
                ])
            
            # 所有者权益合计
            table_data.append([
                Paragraph("<b>所有者权益合计</b>", table_total_style),
                Paragraph(f"{balance_sheet_data.total_equity:,.2f}", table_total_style),
            ])
            
            # 负债和所有者权益合计
            total_liabilities_and_equity = balance_sheet_data.total_liabilities + balance_sheet_data.total_equity
            table_data.append([
                Paragraph("<b>负债和所有者权益合计</b>", table_total_style),
                Paragraph(f"{total_liabilities_and_equity:,.2f}", table_total_style),
            ])
            
            # 创建表格
            table = Table(table_data, colWidths=[12*cm, 6*cm])
            table.setStyle(TableStyle([
                # 表头样式
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # 金额右对齐
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # 表格边框
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                
                # 行高
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 12))
            
            # 平衡验证
            if balance_sheet_data.is_balanced:
                story.append(Paragraph("✓ 报表已平衡（资产 = 负债 + 所有者权益）", header_style))
            else:
                diff = abs(balance_sheet_data.total_assets - total_liabilities_and_equity)
                story.append(Paragraph(f"⚠ 报表不平衡，差异：{diff:,.2f}", header_style))
            
            # AI分析部分（如果提供）
            if ai_analysis:
                story.append(PageBreak())
                story.append(Spacer(1, 12))
                
                # AI分析标题
                analysis_title_style = ParagraphStyle(
                    'AnalysisTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    textColor=colors.black,
                    spaceAfter=12,
                    alignment=1,  # 居中
                )
                story.append(Paragraph("财务分析说明", analysis_title_style))
                story.append(Spacer(1, 12))
                
                # 解析Markdown格式的AI分析内容
                import re
                analysis_lines = ai_analysis.split('\n')
                for line in analysis_lines:
                    line = line.strip()
                    if not line:
                        story.append(Spacer(1, 6))
                        continue
                    
                    # 处理标题
                    if line.startswith('# '):
                        text = line[2:].strip()
                        story.append(Paragraph(text, heading_style))
                        story.append(Spacer(1, 8))
                    elif line.startswith('## '):
                        text = line[3:].strip()
                        story.append(Paragraph(text, heading_style))
                        story.append(Spacer(1, 6))
                    elif line.startswith('### '):
                        text = line[4:].strip()
                        story.append(Paragraph(text, styles['Heading3']))
                        story.append(Spacer(1, 4))
                    # 处理列表
                    elif line.startswith('- ') or line.startswith('* '):
                        text = line[2:].strip()
                        # 移除markdown格式
                        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                        text = re.sub(r'⚠️|✓', '', text)  # 移除emoji
                        story.append(Paragraph(f"• {text}", table_normal_style))
                    # 处理普通文本
                    else:
                        # 移除markdown格式
                        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                        story.append(Paragraph(text, table_normal_style))
            
            logger.debug("开始构建PDF文档")
            # 构建PDF
            doc.build(story)
            
            # 验证PDF文件
            if self._validate_pdf_file(pdf_path):
                logger.info(f"资产负债表PDF已成功生成: {pdf_path}, 大小: {pdf_path.stat().st_size} 字节")
                return str(pdf_path)
            else:
                logger.error(f"PDF文件生成但验证失败: {pdf_path}")
                # 回退到markdown转换方式
                logger.info("尝试使用markdown转换方式作为回退")
                return self._fallback_to_markdown(balance_sheet_data, config, pdf_path)
            
        except ImportError as e:
            logger.error(f"未安装reportlab库，无法生成PDF: {e}", exc_info=True)
            # 回退到markdown转换方式
            return self._fallback_to_markdown(balance_sheet_data, config, pdf_path)
        except Exception as e:
            logger.exception(f"生成资产负债表PDF失败: {e}")
            # 回退到markdown转换方式
            logger.info("尝试使用markdown转换方式作为回退")
            return self._fallback_to_markdown(balance_sheet_data, config, pdf_path)
    
    def _fallback_to_markdown(self, balance_sheet_data: BalanceSheetData, config: ReportConfig, pdf_path: Path) -> Optional[str]:
        """回退到markdown转换方式。
        
        Args:
            balance_sheet_data: 资产负债表数据
            config: 报表配置
            pdf_path: PDF文件路径
            
        Returns:
            Optional[str]: PDF文件路径，失败返回None
        """
        try:
            logger.debug("使用markdown转换方式生成PDF")
            from services.financial_reports.exporters.markdown_exporter import MarkdownExporter
            markdown_exporter = MarkdownExporter()
            markdown_content = markdown_exporter.export_balance_sheet(balance_sheet_data, config)
            if self._markdown_to_pdf(markdown_content, pdf_path):
                if self._validate_pdf_file(pdf_path):
                    logger.info(f"使用markdown转换方式成功生成PDF: {pdf_path}")
                    return str(pdf_path)
            logger.error("markdown转换方式也失败")
            return None
        except Exception as e:
            logger.exception(f"回退到markdown转换方式失败: {e}")
            return None
    
    def export_balance_sheet_from_markdown(self, markdown_content: str, config: ReportConfig) -> Optional[str]:
        """从Markdown内容导出资产负债表为PDF文件（兼容方法）。
        
        Args:
            markdown_content: Markdown格式的报表内容
            config: 报表配置
            
        Returns:
            Optional[str]: PDF文件路径，失败返回None
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = self.reports_dir / f"balance_sheet_{timestamp}.pdf"
        
        logger.info(f"使用markdown转换方式生成资产负债表PDF: {pdf_path}")
        
        if self._markdown_to_pdf(markdown_content, pdf_path):
            # 验证PDF文件
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                logger.info(f"资产负债表PDF验证通过: {pdf_path}, 大小: {pdf_path.stat().st_size} 字节")
                return str(pdf_path)
            else:
                logger.error(f"资产负债表PDF文件验证失败: 文件不存在或为空")
                return None
        return None
    
    def _validate_pdf_file(self, pdf_path: Path) -> bool:
        """验证PDF文件是否存在且有效。
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            bool: 文件是否有效
        """
        if not pdf_path.exists():
            logger.error(f"PDF文件不存在: {pdf_path}")
            return False
        
        file_size = pdf_path.stat().st_size
        if file_size == 0:
            logger.error(f"PDF文件为空: {pdf_path}")
            return False
        
        # 检查文件大小是否合理（至少应该大于100字节）
        if file_size < 100:
            logger.warning(f"PDF文件大小异常小: {pdf_path}, 大小: {file_size} 字节")
            return False
        
        # 检查文件扩展名
        if pdf_path.suffix.lower() != '.pdf':
            logger.warning(f"文件扩展名不是.pdf: {pdf_path}")
        
        logger.debug(f"PDF文件验证通过: {pdf_path}, 大小: {file_size} 字节")
        return True

    def export_income_statement(self, markdown_content: str, config: ReportConfig) -> Optional[str]:
        """导出利润表为PDF文件。
        
        Args:
            markdown_content: Markdown格式的报表内容
            config: 报表配置
            
        Returns:
            Optional[str]: PDF文件路径，失败返回None
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = self.reports_dir / f"income_statement_{timestamp}.pdf"
        
        logger.info(f"开始生成利润表PDF: {pdf_path}")
        
        if self._markdown_to_pdf(markdown_content, pdf_path):
            if self._validate_pdf_file(pdf_path):
                logger.info(f"利润表PDF已成功生成: {pdf_path}, 大小: {pdf_path.stat().st_size} 字节")
                return str(pdf_path)
            else:
                logger.error(f"利润表PDF文件生成但验证失败: {pdf_path}")
                return None
        else:
            logger.error(f"利润表PDF生成失败: {pdf_path}")
            return None

    def export_cash_flow(self, markdown_content: str, config: ReportConfig) -> Optional[str]:
        """导出现金流量表为PDF文件。
        
        Args:
            markdown_content: Markdown格式的报表内容
            config: 报表配置
            
        Returns:
            Optional[str]: PDF文件路径，失败返回None
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = self.reports_dir / f"cash_flow_{timestamp}.pdf"
        
        logger.info(f"开始生成现金流量表PDF: {pdf_path}")
        
        if self._markdown_to_pdf(markdown_content, pdf_path):
            if self._validate_pdf_file(pdf_path):
                logger.info(f"现金流量表PDF已成功生成: {pdf_path}, 大小: {pdf_path.stat().st_size} 字节")
                return str(pdf_path)
            else:
                logger.error(f"现金流量表PDF文件生成但验证失败: {pdf_path}")
                return None
        else:
            logger.error(f"现金流量表PDF生成失败: {pdf_path}")
            return None


__all__ = ["PDFExporter"]
