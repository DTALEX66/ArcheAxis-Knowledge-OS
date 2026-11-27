package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html"
	"os"
	"path/filepath"
	"strings"

	"github.com/88250/lute"
	"github.com/88250/lute/ast"
	"github.com/siyuan-note/dataparser"
)

const imageParent = "20210512171633-u3iy2xx"
const imagePath = "assets/siyuan-128-20210604092205-djd749a.png"
const expectedImageSHA = "788c154262194a126b433b1055fbddcf5ada066e0d1f565a54e5550125675075"

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(args []string) error {
	if len(args) < 2 || len(args) > 4 {
		return fmt.Errorf("usage: native-reader DOCUMENT.sy NOTEBOOK_ROOT [BLOCK_ID [VISIBLE_SENTINEL]]")
	}
	source := args[0]
	notebook := args[1]
	blockID := imageParent
	if len(args) >= 3 {
		blockID = args[2]
	}
	input, err := os.ReadFile(source)
	if err != nil {
		return err
	}
	engine := lute.New()
	engine.ParseOptions.KeepEscaped = true
	engine.SetTextMark(true)
	engine.SetProtyleWYSIWYG(true)
	engine.SetBlockRef(true)
	engine.SetFileAnnotationRef(true)
	engine.SetKramdownIAL(true)
	engine.SetSuperBlock(true)
	engine.SetCustomBlock(true)
	engine.SetImgPathAllowSpace(true)
	engine.SetSanitize(true)
	engine.SetCallout(true)
	engine.SetTabs(true)

	tree, needsFix, err := dataparser.ParseJSON(input, engine.ParseOptions)
	if err != nil {
		return err
	}
	if tree.Root.ID != "20200915214115-42b8zma" {
		return fmt.Errorf("unexpected root ID %q", tree.Root.ID)
	}
	blocks := 0
	var selected *ast.Node
	assetLocated := false
	ast.Walk(tree.Root, func(node *ast.Node, entering bool) ast.WalkStatus {
		if !entering {
			return ast.WalkContinue
		}
		if node.ID == blockID && node.IsBlock() {
			selected = node
		}
		if node.IsBlock() {
			blocks++
		}
		if node.ID == imageParent {
			ast.Walk(node, func(child *ast.Node, enteringChild bool) ast.WalkStatus {
				if enteringChild && child.Type == ast.NodeLinkDest && string(child.Tokens) == imagePath {
					assetLocated = true
				}
				return ast.WalkContinue
			})
		}
		return ast.WalkContinue
	})
	if selected == nil {
		return fmt.Errorf("selected block %s was not found", blockID)
	}
	if !assetLocated {
		return fmt.Errorf("relative image target missing from original block %s", imageParent)
	}
	rendered := engine.Tree2BlockDOM(tree, engine.RenderOptions, engine.ParseOptions)
	if !strings.Contains(rendered, `data-node-id="`+imageParent+`"`) || !strings.Contains(rendered, `data-src="`+imagePath+`"`) {
		return fmt.Errorf("official BlockDOM did not render expected original block and image path")
	}
	if len(args) == 4 && (!strings.Contains(selected.Text(), args[3]) || !strings.Contains(html.UnescapeString(rendered), args[3])) {
		return fmt.Errorf("requested sentinel did not appear in official BlockDOM")
	}
	asset, err := os.ReadFile(filepath.Join(notebook, filepath.FromSlash(imagePath)))
	if err != nil {
		return err
	}
	assetSHA := digest(asset)
	if assetSHA != expectedImageSHA {
		return fmt.Errorf("PNG digest mismatch: %s", assetSHA)
	}
	receipt := map[string]any{
		"scope": "SiYuan dataparser and Lute BlockDOM library readback; PNG byte preservation",
		"lute_version": lute.Version,
		"dataparser_module": "v0.0.0-20260115084335-b57cb8bc7c17",
		"lute_module": "v1.7.9-0.20261113125822-61eb27b6d434",
		"input_filename": filepath.Base(source),
		"input_bytes": len(input),
		"input_sha256": digest(input),
		"document_id": tree.Root.ID,
		"spec_after_parse": tree.Root.Spec,
		"parser_reported_in_memory_normalization": needsFix,
		"block_count_including_document": blocks,
		"blockdom_bytes": len(rendered),
		"blockdom_sha256": digest([]byte(rendered)),
		"selected_block_id": blockID,
		"selected_block_text": selected.Text(),
		"rendered_image_block": imageParent,
		"rendered_image_target": imagePath,
		"png_bytes": len(asset),
		"png_sha256": assetSHA,
	}
	if len(args) == 4 {
		receipt["rendered_sentinel_verified"] = true
	}
	return json.NewEncoder(os.Stdout).Encode(receipt)
}

func digest(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

