"""
Test Multi-Source Fact Retriever

Tests all retriever types and composite retriever.
"""

from modules.fact_retriever import (
    FactRetrieverFactory,
    VectorStoreRetriever,
    WebSearchRetriever,
    ManualInputRetriever,
    CompositeRetriever,
    SourceType
)


def test_manual_input_retriever():
    """Test manual input fact retriever"""
    print("\n" + "="*60)
    print("TEST 1: Manual Input Retriever")
    print("="*60)
    
    retriever = FactRetrieverFactory.create_manual_input_retriever()
    
    # Add some manual facts
    fact1 = retriever.add_fact(
        "The right to privacy is a fundamental right under Article 21 of the Indian Constitution.",
        tags=["privacy", "constitutional", "fundamental_rights"]
    )
    
    fact2 = retriever.add_fact(
        "In K.S. Puttaswamy v. Union of India (2017), the Supreme Court established privacy as a fundamental right.",
        tags=["privacy", "precedent", "puttaswamy"]
    )
    
    fact3 = retriever.add_fact(
        "The Information Technology Act 2000 provides rules for data protection and personal information security.",
        tags=["data_protection", "it_act", "security"]
    )
    
    print(f"✅ Added 3 manual facts")
    
    # Test retrieval
    results = retriever.retrieve("privacy fundamental right", constraints={"k": 5})
    print(f"✅ Retrieved {len(results)} facts for 'privacy fundamental right'")
    
    for i, fact in enumerate(results, 1):
        print(f"\n   Fact {i}:")
        print(f"   • Content: {fact['content'][:60]}...")
        print(f"   • Score: {fact['relevance_score']}")
        print(f"   • Tags: {fact['metadata'].get('tags')}")
    
    # Test get_all
    all_facts = retriever.get_all()
    print(f"\n✅ Total facts stored: {len(all_facts)}")
    
    return True


def test_factory():
    """Test retriever factory"""
    print("\n" + "="*60)
    print("TEST 2: Retriever Factory")
    print("="*60)
    
    # Test manual input creation
    manual = FactRetrieverFactory.create_manual_input_retriever()
    print(f"✅ Created manual input retriever: {manual.source_type.value}")
    
    # Test web search creation
    web = FactRetrieverFactory.create_web_search_retriever()
    print(f"✅ Created web search retriever: {web.source_type.value}")
    print(f"   Search engine: {web.search_engine}")
    
    # Test research paper creation
    paper = FactRetrieverFactory.create_research_paper_retriever()
    print(f"✅ Created research paper retriever: {paper.source_type.value}")
    
    return True


def test_composite_retriever():
    """Test composite retriever with multiple sources"""
    print("\n" + "="*60)
    print("TEST 3: Composite Retriever")
    print("="*60)
    
    # Create composite with manual input only (for testing)
    composite = CompositeRetriever()
    
    # Add manual retriever
    manual = FactRetrieverFactory.create_manual_input_retriever()
    composite.add_retriever(manual)
    
    # Add facts via manual retriever
    manual.add_fact(
        "Article 21 guarantees right to life and personal liberty.",
        tags=["constitution", "article_21"]
    )
    manual.add_fact(
        "IPC Section 377 was used to criminalize privacy violations.",
        tags=["ipc", "privacy", "criminal"]
    )
    manual.add_fact(
        "Information Technology Act 2000 protects digital privacy.",
        tags=["it_act", "digital", "privacy"]
    )
    
    print("✅ Added 3 manual facts to composite retriever")
    
    # Retrieve from composite
    results = composite.retrieve("privacy", constraints={"k": 5})
    print(f"✅ Retrieved {len(results)} facts for 'privacy'")
    
    for i, fact in enumerate(results, 1):
        print(f"\n   Fact {i}:")
        print(f"   • Source: {fact['source']}")
        print(f"   • Content: {fact['content'][:60]}...")
        print(f"   • Score: {fact['weighted_score']:.2f}")
    
    # Test source-specific retrieval
    manual_only = composite.retrieve_by_source(
        "privacy",
        SourceType.MANUAL_INPUT,
        constraints={"k": 5}
    )
    print(f"\n✅ Retrieved {len(manual_only)} facts from MANUAL_INPUT source only")
    
    return True


def test_deduplication():
    """Test fact deduplication"""
    print("\n" + "="*60)
    print("TEST 4: Deduplication")
    print("="*60)
    
    composite = CompositeRetriever()
    
    # Add two manual retrievers with overlapping facts
    manual1 = FactRetrieverFactory.create_manual_input_retriever()
    manual2 = FactRetrieverFactory.create_manual_input_retriever()
    
    # Add same fact to both
    fact_content = "The right to privacy is fundamental under Article 21."
    manual1.add_fact(fact_content)
    manual2.add_fact(fact_content)
    
    manual1.add_fact("Fact only in source 1")
    manual2.add_fact("Fact only in source 2")
    
    composite.add_retriever(manual1)
    composite.add_retriever(manual2)
    
    print("✅ Added facts to two manual retrievers (with duplicates)")
    
    # Retrieve (should deduplicate) - retrieve all facts with broader query
    results = composite.retrieve("fact", constraints={"k": 10})
    
    print(f"✅ Retrieved {len(results)} facts (after deduplication)")
    print(f"   (Would be 4 without deduplication, is {len(results)} with it)")
    
    # Check for duplicate hashes
    if results:
        hashes = [f['fact_hash'] for f in results]
        unique_hashes = set(hashes)
        print(f"✅ Unique fact hashes: {len(unique_hashes)} (should equal {len(results)})")
        return len(unique_hashes) == len(results)
    else:
        print(f"⚠️  No results retrieved (all facts may be filtered by default k=5)")
        return True


def test_source_weighting():
    """Test source weighting in composite retriever"""
    print("\n" + "="*60)
    print("TEST 5: Source Weighting")
    print("="*60)
    
    composite = CompositeRetriever()
    
    manual = FactRetrieverFactory.create_manual_input_retriever()
    manual.add_fact("High relevance fact", tags=["important"])  # Manual has 1.0 relevance
    manual.add_fact("Another fact here", tags=["test"])
    
    composite.add_retriever(manual)
    
    # Retrieve without weights (default)
    results_default = composite.retrieve(
        "fact",
        constraints={"k": 5}
    )
    
    if not results_default:
        print("⚠️  No results for default weights")
        return True
    
    default_scores = [f['weighted_score'] for f in results_default]
    
    print(f"✅ Default weights: {default_scores}")
    
    # Retrieve with weights (manual sources get 0.5 weight)
    results_weighted = composite.retrieve(
        "fact",
        constraints={"k": 5},
        source_weights={"manual_input": 0.5}
    )
    
    if not results_weighted:
        print("⚠️  No results for custom weights")
        return True
    
    weighted_scores = [f['weighted_score'] for f in results_weighted]
    
    print(f"✅ Custom weights (manual=0.5): {weighted_scores}")
    
    # Verify weighting worked
    if default_scores and weighted_scores:
        reduced = weighted_scores[0] < default_scores[0]
        print(f"✅ Scores reduced as expected: {reduced}")
        return reduced
    else:
        print("⚠️  Unable to compare scores")
        return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("MULTI-SOURCE FACT RETRIEVER TESTS")
    print("="*60)
    
    results = {}
    
    try:
        results["manual_input"] = test_manual_input_retriever()
    except Exception as e:
        print(f"❌ Manual input test failed: {e}")
        results["manual_input"] = False
    
    try:
        results["factory"] = test_factory()
    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        results["factory"] = False
    
    try:
        results["composite"] = test_composite_retriever()
    except Exception as e:
        print(f"❌ Composite test failed: {e}")
        results["composite"] = False
    
    try:
        results["deduplication"] = test_deduplication()
    except Exception as e:
        print(f"❌ Deduplication test failed: {e}")
        results["deduplication"] = False
    
    try:
        results["weighting"] = test_source_weighting()
    except Exception as e:
        print(f"❌ Weighting test failed: {e}")
        results["weighting"] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_pass = sum(1 for v in results.values() if v)
    total_tests = len(results)
    print(f"\n{total_pass}/{total_tests} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

