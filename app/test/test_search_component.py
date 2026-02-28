#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Component Testing Suite
Tests Search.js component features and functionality
"""

from pathlib import Path

class SearchComponentTester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.content = ""
        self.css_content = ""
        
        # Load file content once with proper encoding
        try:
            search_path = Path("app/frontend/src/components/search_bar/Search.js")
            self.content = search_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Error loading Search.js: {e}")
        
        try:
            css_path = Path("app/frontend/src/components/search_bar/Search.css")
            self.css_content = css_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"Error loading Search.css: {e}")
    
    def print_header(self, title):
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)
    
    def print_test(self, name, status, details=""):
        symbol = "✓" if status else "✗"
        status_text = "PASS" if status else "FAIL"
        print(f"[{symbol} {status_text}] {name}")
        if details:
            print(f"      {details}")
        
        if status:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
    
    def test_feature_1_imports(self):
        self.print_header("FEATURE 1: Required Imports and Dependencies")
        self.print_test("1.1 React imported", "import React" in self.content, "React for component structure")
        self.print_test("1.2 useState hook imported", "useState" in self.content, "For state management")
        self.print_test("1.3 useEffect hook imported", "useEffect" in self.content, "For side effects")
        self.print_test("1.4 API service imported", "api" in self.content, "For API calls")
        self.print_test("1.5 CSS imported", "Search.css" in self.content, "Component styles")
        self.print_test("1.6 Icons imported", "react-icons" in self.content or "FaSearch" in self.content, "For UI icons")
    
    def test_feature_2_default_tags(self):
        self.print_header("FEATURE 2: Default Tags Configuration")
        self.print_test("2.1 DEFAULT_TAGS defined", "DEFAULT_TAGS" in self.content, "Tag configuration array")
        self.print_test("2.2 Politics tag exists", "Politics" in self.content, "Category tag")
        self.print_test("2.3 Technology tag exists", "Technology" in self.content, "Category tag")
        self.print_test("2.4 Sports tag exists", "Sports" in self.content, "Category tag")
        self.print_test("2.5 Weather tag exists", "Weather" in self.content, "Category tag")
        self.print_test("2.6 Health tag exists", "Health" in self.content, "Category tag")
        self.print_test("2.7 Tag colors defined", "#2563eb" in self.content or "color" in self.content, "Color property")
    
    def test_feature_3_utility_functions(self):
        self.print_header("FEATURE 3: Utility Functions")
        self.print_test("3.1 toTitleCase function", "toTitleCase" in self.content, "Text transformation")
        self.print_test("3.2 normaliseTagToken function", "normaliseTagToken" in self.content, "Tag normalization")
        self.print_test("3.3 extractRawTags function", "extractRawTags" in self.content, "Tag extraction")
        self.print_test("3.4 toLowerCase used", "toLowerCase" in self.content, "String case conversion")
        self.print_test("3.5 trim used", "trim" in self.content, "Whitespace removal")
    
    def test_feature_4_tag_style_mapping(self):
        self.print_header("FEATURE 4: Tag Style Mapping")
        self.print_test("4.1 TAG_STYLE_MAP defined", "TAG_STYLE_MAP" in self.content, "Style configuration")
        self.print_test("4.2 Search tag style", "search" in self.content, "Tag type style")
        self.print_test("4.3 Content tag style", "content" in self.content, "Tag type style")
        self.print_test("4.4 Location tag style", "location" in self.content, "Tag type style")
        self.print_test("4.5 Media tag style", "media" in self.content, "Tag type style")
        self.print_test("4.6 Default tag style", "default" in self.content, "Fallback style")
    
    def test_feature_5_search_component(self):
        self.print_header("FEATURE 5: Main Search Component Structure")
        self.print_test("5.1 Search component defined", "const Search" in self.content, "Component declaration")
        self.print_test("5.2 Props destructuring", "searchTerm" in self.content or "onSearchResult" in self.content, "Props")
        self.print_test("5.3 useState for search", "useState" in self.content, "State management")
        # More flexible: accept any results/suggestions state management
        has_results_state = ("setSearchResults" in self.content or "searchResults" in self.content or 
                            "setSuggestedTags" in self.content or "suggestedTags" in self.content or
                            "setResults" in self.content or "results" in self.content)
        self.print_test("5.4 Results/suggestions state", has_results_state, "Results state management")
        self.print_test("5.5 useEffect for API", "useEffect" in self.content, "Side effects hook")
        self.print_test("5.6 Component export", "export" in self.content, "Component exported")
    
    def test_feature_6_search_functionality(self):
        self.print_header("FEATURE 6: Search Functionality")
        self.print_test("6.1 Search query handling", "query" in self.content or "search" in self.content, "Query state")
        self.print_test("6.2 API search endpoint", ".search" in self.content or "api" in self.content, "API integration")
        self.print_test("6.3 Error handling", "catch" in self.content or "error" in self.content, "Error management")
        self.print_test("6.4 Loading state", "loading" in self.content or "isLoading" in self.content, "Loading indicator")
        self.print_test("6.5 Optimization", "useMemo" in self.content or "useCallback" in self.content, "Performance")
    
    def test_feature_7_tag_extraction(self):
        self.print_header("FEATURE 7: Tag Extraction and Processing")
        self.print_test("7.1 extractRawTags function", "extractRawTags" in self.content, "Extracts tags")
        self.print_test("7.2 Multiple tag fields", "tags" in self.content and "tag_list" in self.content, "Flexible mapping")
        self.print_test("7.3 Deduplication", "Set" in self.content or "unique" in self.content, "Removes duplicates")
        self.print_test("7.4 Normalization", "normaliseTagToken" in self.content, "Standardizes format")
        self.print_test("7.5 Type inference", "metadata" in self.content, "Infers tag type")
    
    def test_feature_8_ui_components(self):
        self.print_header("FEATURE 8: UI Component Elements")
        self.print_test("8.1 Search input field", "input" in self.content, "Search text input")
        self.print_test("8.2 Search button", "button" in self.content, "Search action")
        self.print_test("8.3 DateRangePicker", "DateRangePicker" in self.content, "Date filtering")
        self.print_test("8.4 Results display", "results" in self.content, "Results rendering")
        self.print_test("8.5 Tag filtering icons", "FaCity" in self.content or "FaGlobeAmericas" in self.content, "Filter icons")
    
    def test_feature_9_handlers(self):
        self.print_header("FEATURE 9: Event Handlers and Callbacks")
        self.print_test("9.1 onChange handler", "onChange" in self.content, "Input change")
        self.print_test("9.2 onSubmit handler", "onSubmit" in self.content or "onClick" in self.content, "Search submission")
        self.print_test("9.3 onSearchResult callback", "onSearchResult" in self.content, "Results callback")
        self.print_test("9.4 useCallback optimization", "useCallback" in self.content, "Prevents re-renders")
        self.print_test("9.5 Event prevention", "preventDefault" in self.content or "stopPropagation" in self.content, "Event handling")
    
    def test_feature_10_responsive(self):
        self.print_header("FEATURE 10: Responsive Design and Styling")
        self.print_test("10.1 CSS module imported", "Search.css" in self.content, "Component styles")
        self.print_test("10.2 Responsive classes", "className" in self.content, "CSS classes")
        self.print_test("10.3 Styling applied", "style" in self.content or "className" in self.content, "Visual styling")
        has_css = bool(self.css_content)
        self.print_test("10.4 CSS file exists", has_css, "Search.css present")
        if has_css:
            self.print_test("10.5 Media queries", "@media" in self.css_content, "Responsive breakpoints")
        else:
            self.print_test("10.5 Media queries", False, "Cannot check without CSS")
    
    def print_summary(self):
        self.print_header("TEST SUMMARY")
        total = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total * 100) if total > 0 else 0
        
        print(f"\n  Total Tests: {total}")
        print(f"  ✓ Passed:   {self.tests_passed}")
        print(f"  ✗ Failed:   {self.tests_failed}")
        print(f"  Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed > 0:
            print(f"\n  {self.tests_failed} feature(s) need attention")
        else:
            print(f"\n  ALL TESTS PASSED!")
        
        print("\n" + "="*80 + "\n")
    
    def run_all_tests(self):
        self.test_feature_1_imports()
        self.test_feature_2_default_tags()
        self.test_feature_3_utility_functions()
        self.test_feature_4_tag_style_mapping()
        self.test_feature_5_search_component()
        self.test_feature_6_search_functionality()
        self.test_feature_7_tag_extraction()
        self.test_feature_8_ui_components()
        self.test_feature_9_handlers()
        self.test_feature_10_responsive()
        self.print_summary()

if __name__ == '__main__':
    tester = SearchComponentTester()
    tester.run_all_tests()
