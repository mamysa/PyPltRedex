test:
	python3 -m unittest tests/test_inholechecker.py
	python3 -m unittest tests/test_holereachability.py
	python3 -m unittest tests/test_cyclecheck.py
	python3 -m unittest tests/test_runtime.py
