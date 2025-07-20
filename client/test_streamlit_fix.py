#!/usr/bin/env python3
"""
Comprehensive test suite to verify Streamlit UI compatibility and API functionality.
Tests various search scenarios including PDF documents, Excel files, and mixed searches.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# ANSI color codes for better output formatting
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

app_url_local = "http://localhost:8004"

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{'='*80}")
    print(f"🧪 {text}")
    print(f"{'='*80}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")


def analyze_response_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the API response structure for Streamlit compatibility."""
    analysis = {
        'has_best_result': False,
        'best_result_source': None,
        'best_result_strategy': None,
        'answer_length': 0,
        'has_pandas_results': False,
        'pandas_results_count': 0,
        'has_document_results': False,
        'document_result_length': 0,
        'search_successful': False,
        'search_strategy': None,
        'streamlit_compatible': False,
        'issues': []
    }
    
    try:
        # Check summary
        summary = data.get('summary', {})
        analysis['search_successful'] = summary.get('search_successful', False)
        analysis['search_strategy'] = summary.get('search_strategy', 'unknown')
        analysis['has_pandas_results'] = summary.get('has_pandas_results', False)
        analysis['has_document_results'] = summary.get('has_document_results', False)
        
        # Check best_result
        best_result = data.get('best_result', {})
        if best_result:
            analysis['has_best_result'] = True
            analysis['best_result_source'] = best_result.get('source')
            analysis['best_result_strategy'] = best_result.get('search_strategy')
            
            answer = best_result.get('answer', '')
            analysis['answer_length'] = len(answer)
            
            if answer:
                analysis['streamlit_compatible'] = True
            else:
                analysis['issues'].append("Best result has no answer")
        else:
            analysis['issues'].append("No best_result found")
        
        # Check pandas agent results
        pandas_search = data.get('pandas_agent_search', {})
        pandas_results = pandas_search.get('results', [])
        analysis['pandas_results_count'] = len(pandas_results)
        analysis['has_pandas_results'] = len(pandas_results) > 0
        
        # Check document search results
        document_search = data.get('document_search', {})
        doc_result = document_search.get('result')
        if doc_result:
            analysis['has_document_results'] = True
            if isinstance(doc_result, dict):
                doc_result = doc_result.get('result', str(doc_result))
            analysis['document_result_length'] = len(str(doc_result))
        
    except Exception as e:
        analysis['issues'].append(f"Error analyzing response: {str(e)}")
    
    return analysis


def test_scenario(scenario_name: str, search_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test a specific scenario and analyze the results."""
    print_header(f"TESTING SCENARIO: {scenario_name}")
    
    print(f"{Colors.BOLD}Query:{Colors.ENDC} {search_data['query']}")
    print(f"{Colors.BOLD}Source:{Colors.ENDC} {search_data['source_document']}")
    print(f"{Colors.BOLD}Debug:{Colors.ENDC} {search_data['debug']}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            app_url_local + "/hybridsearch/",
            json=search_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        response_time = time.time() - start_time
        
        print(f"\n{Colors.BOLD}Response Time:{Colors.ENDC} {response_time:.2f}s")
        print(f"{Colors.BOLD}Status Code:{Colors.ENDC} {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            analysis = analyze_response_structure(data)
            
            print(f"\n{Colors.BOLD}=== DETAILED ANALYSIS ==={Colors.ENDC}")
            
            # Search strategy and success
            print(f"Search Strategy: {analysis['search_strategy']}")
            print(f"Search Successful: {analysis['search_successful']}")
            print(f"Has Document Results: {analysis['has_document_results']}")
            print(f"Has Pandas Results: {analysis['has_pandas_results']}")
            
            # Best result analysis
            if analysis['has_best_result']:
                print_success(f"Best Result Found:")
                print(f"  Source: {analysis['best_result_source']}")
                print(f"  Strategy: {analysis['best_result_strategy']}")
                print(f"  Answer Length: {analysis['answer_length']}")
                
                if analysis['answer_length'] > 0:
                    answer = data['best_result']['answer']
                    preview = answer[:200] if len(answer) > 200 else answer
                    print(f"  Answer Preview: {preview}...")
                    print_success("Streamlit will display this result!")
                else:
                    print_error("No answer in best_result!")
            else:
                print_error("No best_result found!")
            
            # Pandas agent results
            if analysis['has_pandas_results']:
                print_success(f"Pandas Agent Results Found:")
                print(f"  Results Count: {analysis['pandas_results_count']}")
                pandas_search = data.get('pandas_agent_search', {})
                for i, result in enumerate(pandas_search.get('results', [])):
                    filename = result.get('filename', 'Unknown')
                    answer_length = len(result.get('answer', ''))
                    print(f"  Result {i+1}: {filename} - Answer length: {answer_length}")
            else:
                print_warning("No pandas agent results!")
            
            # Document search results
            if analysis['has_document_results']:
                print_success(f"Document Search Results Found:")
                print(f"  Document Result Length: {analysis['document_result_length']}")
            else:
                print_warning("No document search results!")
            
            # Overall assessment
            print(f"\n{Colors.BOLD}📊 OVERALL ASSESSMENT:{Colors.ENDC}")
            if analysis['search_successful']:
                print_success("Search was successful")
                if analysis['streamlit_compatible']:
                    print_success("Streamlit will display results correctly!")
                    print_success("Will show: '🔍 Search completed successfully!'")
                    print_success("Will display answer in '🎯 Best Answer:' section")
                else:
                    print_error("Streamlit will show 'No results found'")
            else:
                print_error("Search was not successful")
                print_error("Streamlit will show 'No results found'")
            
            # Report issues
            if analysis['issues']:
                print(f"\n{Colors.BOLD}⚠️  ISSUES FOUND:{Colors.ENDC}")
                for issue in analysis['issues']:
                    print_warning(issue)
            
            return {
                'scenario': scenario_name,
                'success': True,
                'response_time': response_time,
                'analysis': analysis,
                'data': data
            }
            
        else:
            print_error(f"HTTP Error: {response.status_code}")
            print_error(f"Response: {response.text}")
            return {
                'scenario': scenario_name,
                'success': False,
                'response_time': response_time,
                'error': f"HTTP {response.status_code}: {response.text}"
            }
            
    except requests.exceptions.ConnectionError:
        print_error("Connection refused. Is the server running on localhost:8004?")
        return {
            'scenario': scenario_name,
            'success': False,
            'error': "Connection refused"
        }
    except requests.exceptions.Timeout:
        print_error("Request timed out")
        return {
            'scenario': scenario_name,
            'success': False,
            'error': "Request timed out"
        }
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return {
            'scenario': scenario_name,
            'success': False,
            'error': str(e)
        }


def test_edge_cases() -> List[Dict[str, Any]]:
    """Test edge cases and error conditions."""
    print_header("TESTING EDGE CASES")
    
    edge_cases = [
        {
            "name": "Empty Query",
            "data": {"query": "", "source_document": "Sample1.pdf", "debug": False}
        },
        {
            "name": "Very Long Query",
            "data": {"query": "This is a very long query that tests how the system handles extremely long queries with many words and complex sentences that might exceed normal limits", "source_document": "Sample1.pdf", "debug": False}
        },
        {
            "name": "Non-existent File",
            "data": {"query": "test query", "source_document": "nonexistent.pdf", "debug": False}
        },
        {
            "name": "Special Characters",
            "data": {"query": "What's the revenue for Q1? (FY25)", "source_document": "nvidia_quarterly_revenue_trend_by_market.xlsx", "debug": False}
        }
    ]
    
    results = []
    for case in edge_cases:
        result = test_scenario(f"Edge Case: {case['name']}", case['data'])
        results.append(result)
    
    return results


def generate_summary_report(all_results: List[Dict[str, Any]]):
    """Generate a comprehensive summary report."""
    print_header("COMPREHENSIVE TEST SUMMARY")
    
    successful_tests = [r for r in all_results if r.get('success', False)]
    failed_tests = [r for r in all_results if not r.get('success', False)]
    
    print(f"{Colors.BOLD}📊 TEST STATISTICS:{Colors.ENDC}")
    print(f"Total Tests: {len(all_results)}")
    print_success(f"Successful: {len(successful_tests)}")
    print_error(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {(len(successful_tests)/len(all_results)*100):.1f}%")
    
    if successful_tests:
        avg_response_time = sum(r.get('response_time', 0) for r in successful_tests) / len(successful_tests)
        print(f"Average Response Time: {avg_response_time:.2f}s")
    
    print(f"\n{Colors.BOLD}✅ SUCCESSFUL SCENARIOS:{Colors.ENDC}")
    for result in successful_tests:
        scenario = result.get('scenario', 'Unknown')
        analysis = result.get('analysis', {})
        streamlit_compatible = analysis.get('streamlit_compatible', False)
        status = "✅ Streamlit Ready" if streamlit_compatible else "⚠️ Needs Attention"
        print(f"  {scenario}: {status}")
    
    if failed_tests:
        print(f"\n{Colors.BOLD}❌ FAILED SCENARIOS:{Colors.ENDC}")
        for result in failed_tests:
            scenario = result.get('scenario', 'Unknown')
            error = result.get('error', 'Unknown error')
            print(f"  {scenario}: {error}")
    
    print(f"\n{Colors.BOLD}🎯 STREAMLIT UI COMPATIBILITY:{Colors.ENDC}")
    streamlit_ready = sum(1 for r in successful_tests if r.get('analysis', {}).get('streamlit_compatible', False))
    print_success(f"Streamlit Ready: {streamlit_ready}/{len(successful_tests)} scenarios")
    
    if streamlit_ready == len(successful_tests):
        print_success("🎉 ALL TESTS PASSED! Streamlit UI is fully compatible!")
    else:
        print_warning(f"⚠️  {len(successful_tests) - streamlit_ready} scenarios need attention")


def test_streamlit_display():
    """Comprehensive test suite for Streamlit UI compatibility."""
    print_header("STREAMLIT UI COMPATIBILITY TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Core scenarios
    core_scenarios = [
        {
            "name": "1. PDF Document Search",
            "data": {
                "query": "Who prepared the document Lot number :01225?",
                "source_document": "Sample1.pdf",
                "debug": False
            }
        },
        {
            "name": "2. All Documents Search",
            "data": {
                "query": "Who prepared the document Lot number :01225?",
                "source_document": "all",
                "debug": False
            }
        },
        {
            "name": "3. Excel File Search",
            "data": {
                "query": "What was NVIDIA's total revenue in Q1 FY25?",
                "source_document": "nvidia_quarterly_revenue_trend_by_market.xlsx",
                "debug": False
            }
        },
        {
            "name": "4. All Documents for Excel Data",
            "data": {
                "query": "What was NVIDIA's total revenue in Q1 FY25?",
                "source_document": "all",
                "debug": False
            }
        },
        {
            "name": "5. Mixed Content Query",
            "data": {
                "query": "What are the key ingredients and revenue trends?",
                "source_document": "all",
                "debug": False
            }
        },
        {
            "name": "6. Specific Data Query",
            "data": {
                "query": "What is the gaming market revenue in Q2?",
                "source_document": "nvidia_quarterly_revenue_trend_by_market.xlsx",
                "debug": False
            }
        }
    ]
    
    # Test core scenarios
    all_results = []
    for scenario in core_scenarios:
        result = test_scenario(scenario['name'], scenario['data'])
        all_results.append(result)
    
    # Test edge cases
    edge_results = test_edge_cases()
    all_results.extend(edge_results)
    
    # Generate summary report
    generate_summary_report(all_results)
    
    print_header("TEST SUITE COMPLETED")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    test_streamlit_display() 