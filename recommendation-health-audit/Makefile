.PHONY: test check plan refresh

test:
	python3 -m unittest discover -s tests -v

check:
	python3 analyze.py --check

plan:
	python3 experiment_design.py

refresh:
	python3 analyze.py

