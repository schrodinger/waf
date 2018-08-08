#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2016-2018 (ita)

from collections import namedtuple
import re

from waflib import Utils

INC_REGEX = """(?:^|['">]\s*;)\s*(?:|#\s*)INCLUDE\s+(?:\w+_)?[<"'](.+?)(?=["'>])"""
USE_REGEX = """(?:^|;)\s*USE(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""
MOD_REGEX = """(?:^|;)\s*MODULE(?!\s*PROCEDURE)(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""

re_inc = re.compile(INC_REGEX, re.I|re.M)
re_use = re.compile(USE_REGEX, re.I|re.M)
re_mod = re.compile(MOD_REGEX, re.I|re.M)

DEPS_CACHE_SIZE = 100000
FILE_CACHE_SIZE = 100000

Deps = namedtuple('Deps', ['incs', 'uses', 'mods'])

class fortran_parser(object):
	"""
	This parser returns:

	* the nodes corresponding to the module names to produce
	* the nodes corresponding to the include files used
	* the module names used by the fortran files
	"""
	def __init__(self, incpaths):
		self.seen = set()
		"""Files already parsed"""

		self.nodes = []
		"""List of :py:class:`waflib.Node.Node` representing the dependencies to return"""

		self.names = []
		"""List of module names to return"""

		self.incpaths = incpaths
		"""List of :py:class:`waflib.Node.Node` representing the include paths"""

	def find_deps(self, node):
		"""
		Parses a Fortran file to obtain the dependencies used/provided

		:param node: fortran file to read
		:type node: :py:class:`waflib.Node.Node`
		:return: lists representing the includes, the modules used, and the modules created by a fortran file
		:rtype: tuple of list of strings
		"""
		try:
			cache = node.ctx.cache_fc_scan_deps
		except AttributeError:
			cache = node.ctx.cache_fc_scan_deps = Utils.lru_cache(DEPS_CACHE_SIZE)
		try:
			return cache[node]
		except KeyError:
			txt = node.read()
			deps = Deps(
				incs=re_inc.findall(txt),
				uses=re_use.findall(txt),
				mods=re_mod.findall(txt),
			)
			cache[node] = deps
			return deps

	def start(self, node):
		"""
		Start parsing. Use the stack ``self.waiting`` to hold nodes to iterate on

		:param node: fortran file
		:type node: :py:class:`waflib.Node.Node`
		"""
		self.waiting = [node]
		while self.waiting:
			nd = self.waiting.pop(0)
			self.iter(nd)

	def iter(self, node):
		"""
		Processes a single file during dependency parsing. Extracts files used
		modules used and modules provided.
		"""
		if node in self.seen:
			return
		deps = self.find_deps(node)
		self.seen.add(node)
		for x in deps.incs:
			if x in self.seen:
				continue
			self.seen.add(x)
			self.tryfind_header(x)

		for x in deps.uses:
			name = "USE@%s" % x
			if not name in self.names:
				self.names.append(name)

		for x in deps.mods:
			name = "MOD@%s" % x
			if not name in self.names:
				self.names.append(name)

	def tryfind_header(self, filename):
		"""
		Adds an include file to the list of nodes to process

		:param filename: file name
		:type filename: string
		"""
		found = None
		for n in self.incpaths:
			found = self.cached_find_resource(n, filename)
			if found:
				self.nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.names:
				self.names.append(filename)

	def cached_find_resource(self, node, filename):
		"""
		Find a file from the input directory

		:param node: directory
		:type node: :py:class:`waflib.Node.Node`
		:param filename: header to find
		:type filename: string
		:return: the node if found, or None
		:rtype: :py:class:`waflib.Node.Node`
		"""
		try:
			cache = node.ctx.cache_fc_scan_node
		except AttributeError:
			cache = node.ctx.cache_fc_scan_node = Utils.lru_cache(FILE_CACHE_SIZE)

		key = (node, filename)
		try:
			return cache[key]
		except KeyError:
			ret = node.find_resource(filename)
			cache[key] = ret
			return ret
