"""
PDF Text Extraction Tool

This module provides functions to extract text content from PDF files.
Uses PyMuPDF (fitz) library for PDF processing.
"""

import fitz  # PyMuPDF
from typing import Union, BinaryIO
import io

from src.errors import PDFExtractionError, PDFTooShortError, PDFCorruptedError


def extract_text_from_pdf(pdf_source: Union[str, bytes, BinaryIO]) -> str:
    """
    Extract all text content from a PDF file.

    This function can handle:
    - File paths (string)
    - Bytes (from file.read())
    - File-like objects (from Streamlit's file_uploader)

    Args:
        pdf_source: Either a file path, bytes, or file-like object

    Returns:
        str: All text content from the PDF, with pages separated by newlines

    Raises:
        ValueError: If the PDF cannot be opened or is invalid
        FileNotFoundError: If the file path doesn't exist

    Example:
        # From a file path
        text = extract_text_from_pdf("proposal.pdf")

        # From Streamlit file uploader
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        if uploaded_file:
            text = extract_text_from_pdf(uploaded_file)
    """

    try:
        # Handle different input types
        if isinstance(pdf_source, str):
            # It's a file path
            doc = fitz.open(pdf_source)
        elif isinstance(pdf_source, bytes):
            # It's bytes data
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            # It's a file-like object (e.g., from Streamlit)
            # Read the bytes and open
            pdf_bytes = pdf_source.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Extract text from all pages
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()

            if page_text.strip():  # Only add non-empty pages
                text_parts.append(f"--- Page {page_num + 1} ---")
                text_parts.append(page_text)

        # Close the document
        doc.close()

        # Join all text with newlines
        full_text = "\n".join(text_parts)

        return full_text

    except FileNotFoundError:
        filename = pdf_source if isinstance(pdf_source, str) else "uploaded file"
        raise PDFExtractionError(f"PDF file not found: {filename}", filename)
    except fitz.FileDataError as e:
        filename = pdf_source if isinstance(pdf_source, str) else getattr(pdf_source, 'name', 'uploaded file')
        raise PDFCorruptedError(filename, str(e))
    except Exception as e:
        filename = pdf_source if isinstance(pdf_source, str) else getattr(pdf_source, 'name', 'uploaded file')
        raise PDFExtractionError(f"Error reading PDF: {str(e)}", filename)


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """
    Extract text from a Streamlit uploaded file object.

    This is a convenience wrapper specifically for Streamlit's file_uploader.

    Args:
        uploaded_file: A Streamlit UploadedFile object

    Returns:
        str: All text content from the PDF

    Example:
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        if uploaded_file:
            text = extract_text_from_uploaded_file(uploaded_file)
            st.write(f"Extracted {len(text)} characters")
    """

    if uploaded_file is None:
        raise ValueError("No file provided")

    # Reset file pointer to beginning (in case it was read before)
    uploaded_file.seek(0)

    # Use the main extraction function
    return extract_text_from_pdf(uploaded_file)


def get_pdf_info(pdf_source: Union[str, bytes, BinaryIO]) -> dict:
    """
    Get basic information about a PDF file.

    Args:
        pdf_source: Either a file path, bytes, or file-like object

    Returns:
        dict: Information about the PDF including:
            - page_count: Number of pages
            - char_count: Total character count
            - has_text: Whether the PDF contains extractable text

    Example:
        info = get_pdf_info("proposal.pdf")
        print(f"Pages: {info['page_count']}")
    """

    try:
        # Handle different input types
        if isinstance(pdf_source, str):
            doc = fitz.open(pdf_source)
        elif isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            # File-like object - need to read and reset
            current_pos = pdf_source.tell()
            pdf_bytes = pdf_source.read()
            pdf_source.seek(current_pos)  # Reset to original position
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Count pages and characters
        page_count = len(doc)
        total_chars = 0

        for page_num in range(page_count):
            page = doc[page_num]
            total_chars += len(page.get_text())

        doc.close()

        return {
            'page_count': page_count,
            'char_count': total_chars,
            'has_text': total_chars > 0
        }

    except Exception as e:
        return {
            'page_count': 0,
            'char_count': 0,
            'has_text': False,
            'error': str(e)
        }


def validate_pdf(pdf_source: Union[str, bytes, BinaryIO]) -> tuple:
    """
    Validate that a file is a valid PDF with extractable text.

    Args:
        pdf_source: Either a file path, bytes, or file-like object

    Returns:
        tuple: (is_valid: bool, message: str)

    Example:
        is_valid, message = validate_pdf(uploaded_file)
        if not is_valid:
            st.error(message)
    """

    info = get_pdf_info(pdf_source)

    if 'error' in info:
        return False, f"Invalid PDF: {info['error']}"

    if info['page_count'] == 0:
        return False, "PDF has no pages"

    if not info['has_text']:
        return False, "PDF has no extractable text (might be scanned images)"

    if info['char_count'] < 100:
        return False, f"PDF has very little text ({info['char_count']} characters)"

    return True, f"Valid PDF: {info['page_count']} pages, {info['char_count']} characters"
